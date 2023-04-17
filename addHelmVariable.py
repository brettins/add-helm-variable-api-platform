import os
import yaml

from configparser import ConfigParser

def main():
    variable_name = input("What is the variable name in all caps? (Example: DATABASE_NAME) ")
    variable_key = f"php-{variable_name.lower().replace('_', '-')}"
    print(f"Generated variable key: {variable_key}")
    variable_key_lower_camel_case = ''.join(word.lower() if i == 0 else word.capitalize() for i, word in enumerate(variable_name.lower().split('_')))

    print(f"Generated variable key in kebab case: {variable_key}")
    print(f"Generated variable key in lowerCamelCase: {variable_key_lower_camel_case}")

    is_secret = input("Is this variable a secret? ('y' for yes, 'n' for no): ")

    # read the ini file
    config = ConfigParser()
    config.read('settings.ini')

    parent_dir = os.path.dirname(os.getcwd())
    helm_path = os.path.join(parent_dir, "helm/api-platform")
    deployment_path = os.path.join(helm_path, "templates/deployment.yaml")

    prod_kube_script = config.get('scripts_filenames', 'prod')
    staging_kube_script = config.get('scripts_filenames', 'staging')

    prod_file = os.path.join(helm_path, config.get('values_filenames', 'prod'))
    staging_file = os.path.join(helm_path, config.get('values_filenames', 'staging'))

    with open(deployment_path, "r") as f:
        deployment_lines = f.readlines()

    insertion_index = -1
    for i, line in enumerate(deployment_lines):
        if (is_secret.lower() in ["n", "no"] and "# EKITABU DEFINED CONFIG MAPS" in line) or \
           (is_secret.lower() in ["y", "yes"] and "# EKITABU DEFINED SECRETS" in line):
            insertion_index = i + 1
            break

    if is_secret.lower() in ["y", "yes"]:
        variable_block = f"""            - name: {variable_name}
              valueFrom:
                secretKeyRef:
                  name: {{{{ include "api-platform.fullname" . }}}}
                  key: {variable_key}
"""
        secrets_path = os.path.join(helm_path, "templates/secrets.yaml")
        with open(secrets_path, "a") as f:
            f.write(f"\n  {variable_key}: {{{{ .Values.php.{variable_key_lower_camel_case} | default (randAlphaNum 40) | b64enc | quote }}}}\n")
        print("Added the variable key and a randomly generated value to secrets.yaml.")

    else:
        variable_block = f"""            - name: {variable_name}
              valueFrom:
                configMapKeyRef:
                  name: {{{{ include "api-platform.fullname" . }}}}
                  key: {variable_key}
"""
        configmap_path = os.path.join(helm_path, "templates/configmap.yaml")
        with open(configmap_path, "a") as f:
            f.write(f"\n  {variable_key}: {{{{ .Values.php.{variable_key_lower_camel_case} }}}}\n")
        print("Added the variable key and value to configmap.yaml.")

    deployment_lines.insert(insertion_index, variable_block)

    with open(deployment_path, "w") as f:
        f.writelines(deployment_lines)
    print("Wrote the modified deployment file back to disk.")

    if is_secret.lower() in ["y", "yes"]:
        upgrade_helm_append = f""" --set php.{variable_key_lower_camel_case}=${{{{ secrets.{variable_name} }}}}"""

        workflow_files = [prod_kube_script, staging_kube_script]
        for workflow_path in workflow_files:
            print(f"Checking {workflow_path}...")
            with open(os.path.join(parent_dir, f".github/workflows/{workflow_path}"), "r") as f:
                workflow_lines = f.readlines()

                # find the line with the helm upgrade command
                helm_upgrade_line = None
                for i, line in enumerate(workflow_lines):
                    if "helm upgrade" in line:
                        helm_upgrade_line = i
                        break

                if helm_upgrade_line is None:
                    print(f"Error: Could not find helm upgrade command in {workflow_path}. Skipping...")
                    continue

                workflow_lines[helm_upgrade_line] = workflow_lines[helm_upgrade_line].rstrip() + upgrade_helm_append
                print(f"Added variable {variable_key_lower_camel_case} to helm upgrade command in {workflow_path}.")

            with open(os.path.join(parent_dir, f".github/workflows/{workflow_path}"), "w") as f:
                f.writelines(workflow_lines)
            print(f"Wrote modified {workflow_path} back to disk.\n")
    else:
        # Get default value for staging from user input
        staging_default = input("What is the default value for staging? (leave blank for no default) ")
        prod_default = input("Enter a default value for prod (leave blank for same as staging): ")

        if not prod_default.strip():
            prod_default = staging_default


        # Write value to staging file if there is a default value
        if staging_default:
            with open(staging_file, 'r+') as f:
                data = yaml.safe_load(f)
                data['php'][variable_key_lower_camel_case] = staging_default
                f.seek(0)
                yaml.safe_dump(data, f, default_flow_style=False)
        else:
            print("No default value provided for staging. Skipping...")
        
        if prod_default.strip():
            with open(prod_file, 'r+') as f:
                data = yaml.safe_load(f)
                data['php'][variable_key_lower_camel_case] = prod_default
                f.seek(0)
                yaml.safe_dump(data, f, default_flow_style=False)
        else:
            print("No default value provided for prod. Skipping...")


if __name__ == "__main__":
    main()
