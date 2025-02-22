import mimetypes
from urllib import request
from django.shortcuts import render
from django.http import HttpResponse , JsonResponse
from rest_framework.decorators import api_view, renderer_classes
from rest_framework import status
from typing import List, Dict
import os
import shutil
import yaml
import csv
from django.shortcuts import render
from .models import LLMModel,APIDetails
import json
import msal
import requests 
from dotenv import load_dotenv
load_dotenv()
from .models import *
import os
from azure.identity import DefaultAzureCredential
from rest_framework.response import Response
from .serializers import *
from .models import APIDetails
from .serializers import APIDetailsSerializer,BlobDataSerializer
import ast
import pandas as pd
import sys
import base64
import json
import atexit
import functools
import os
import re
import sys
from datetime import datetime


repo_path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(repo_path)

from taskweaver.app.app import TaskWeaverApp  # Import TaskWeaverApp
from taskweaver.memory.attachment import AttachmentType
from taskweaver.memory.type_vars import RoleName
from taskweaver.module.event_emitter import PostEventType, RoundEventType, SessionEventHandlerBase,SessionEventHandler,TaskWeaverEvent
from taskweaver.session.session import Session
from typing import Any, Dict, List, Optional, Tuple, Union
from taskweaver.code_interpreter import code_executor
from taskweaver.memory.plugin import set_plugin_folder
from azure.identity import DefaultAzureCredential
from langchain_openai import AzureChatOpenAI
from azure.core.credentials import AccessToken
from ruamel.yaml import YAML
import logging as log
from django.http import StreamingHttpResponse
project_path = os.path.join(repo_path, "project")
app = TaskWeaverApp(app_dir=project_path, use_local_uri=True)
atexit.register(app.stop)


app_session_dict: Dict[str, Session] = {}
user_session_id = ""
app_session_dict[user_session_id] = app.get_session()
session=""
python_code_content=""
yaml_code_content=""

plugin_name=""
plugin_description=""

code_executor.set_plugin_folder("adminplugins")
set_plugin_folder("adminplugins")

admin_project_path = os.path.join(repo_path, "project")
adminapp = TaskWeaverApp(app_dir=admin_project_path, use_local_uri=True)
print("$"*15,admin_project_path)
atexit.register(adminapp.stop)
admin_session_dict: Dict[str, Session] = {}
admin_session_id = ""
admin_session_dict[admin_session_id] = adminapp.get_session()
adminsession=""

code_executor.set_plugin_folder("draftplugins")
set_plugin_folder("draftplugins")

draft_project_path = os.path.join(repo_path, "project")
draftapp = TaskWeaverApp(app_dir=draft_project_path, use_local_uri=True)
print("$"*15,draft_project_path)
atexit.register(draftapp.stop)
draft_session_dict: Dict[str, Session] = {}
draft_session_id = ""
draft_session_dict[draft_session_id] = draftapp.get_session()
draftsession=""
from rest_framework.renderers import BaseRenderer

# class ServerSentEventRenderer(BaseRenderer):
#     media_type = 'text/event-stream'
#     format = 'txt'

#     def render(self, data, accepted_media_type=None, renderer_context=None):
#         return data

# @api_view(['GET'])
# # Add the custom renderer to the view
# @renderer_classes([ServerSentEventRenderer])
# def chatgpt(request):
#     def event_stream():
#         for i in range(0,10):
#             data =1
#             yield f'data: {data}\n\n'

#     response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
#     response['X-Accel-Buffering'] = 'no'  # Disable buffering in nginx
#     response['Cache-Control'] = 'no-cache'  # Ensure clients don't cache the data
#     return response

@api_view(['GET'])
def IsAuthorize(request):
    """
    descrption: Username name fetches from the frontend.Based on MSAL the accesstoken is fetched. This token is used
        to get the members information of the particular group using graph url.Once the memeber info is fetched. It
        loops through all member info based on UserPricipalName. If UserPricipalName Matches with username it send true to
        frontend if not it send false to frontend.
    parameter:request-used to get the username from headers.
    returns:Returns as JSON in the format {Access:True/False}
    """
    #Get the username from the headers request
    username=request.headers.get('username')
    config = {
  'client_id': os.getenv("ClientId"),
  'client_secret':os.getenv("ClientSecret"),
  'authority': os.getenv("Instance")+os.getenv("TenantId"),
  'scope': ['https://graph.microsoft.com/.default']
    }
    client = msal.ConfidentialClientApplication(config['client_id'], authority=config['authority'], client_credential=config['client_secret'])
    url = 'https://graph.microsoft.com/v1.0/groups/'+os.getenv("GroupId_1")+'/members'
    pagination=False
      # Firstly, try to lookup an access token in cache
    token_result = client.acquire_token_silent(config['scope'], account=None)

    # Log that token was loaded from the cache
    if token_result:
        print('Access token was loaded from cache.')

    # If token not available in cache, acquire a new one from Azure AD
    if not token_result:
        token_result = client.acquire_token_for_client(scopes=config['scope'])
        print('New access token aquired from AAD')

    # If token available, execute Graph query
    if 'access_token' in token_result:
        headers = {'Authorization': 'Bearer ' + token_result['access_token']}
        azure_group_members = []
        azure_group = requests.get(url=url, headers=headers).json()
        azure_group_members.extend(azure_group['value'])
        if (pagination == True):
            url = azure_group['@odata.nextLink']
        else:
            url = None
    else:
        print(token_result.get('error'))
        print(token_result.get('error_description'))
        print(token_result.get('correlation'))
    #Cheking the username with the UserPrincipalName from the graph response
    is_username_present = any(user["userPrincipalName"] == username for user in azure_group_members)
    return JsonResponse({"Access":is_username_present},safe=False)


@api_view(['GET'])
def list_plugins(request):

    """
    Retrieves a list of plugins from the plugins folder, including their names,
    descriptions, examples, parameters, return values, and enabled statuses.
   
    This function reads each `.yaml` file in the plugins folder and extracts
    details such as `plugin_name`, `description`, `example`, `parameters`,
    `return values`, and `enabled_status`. If a field is missing, it provides a
    default message. It also updates a CSV file with these details.
   
    Returns:
        A list of dictionaries, each containing:
        - `plugin_name` (str): Name of the plugin file without extension
        - `description` (str): Plugin description or a default message
        - `example` (str): Example usage of the function
        - `parameter_description` (str): Description of parameters
        - `return_description` (str): Description of return values
        - `enabled_status` (str): Enabled status
    """ 
    # plugins_folder = os.path.join(os.pardir, 'project', 'plugins')
    # plugins_folder_path = os.path.abspath(plugins_folder)
    plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
    csv_file_path = 'plugins.csv'
 
    # Get all .yaml files from the plugins folder
    yaml_files = [f for f in os.listdir(plugins_folder_path) if f.endswith('.yaml') and os.path.isfile(os.path.join(plugins_folder_path, f))]
    # Load existing plugin details from CSV into a dictionary for easy lookup
    existing_plugins = {}
    if os.path.exists(csv_file_path):
        with open(csv_file_path, mode='r') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                existing_plugins[row['plugin_name']] = row
    plugins = []
    for yaml_file in yaml_files:
        file_path = os.path.join(plugins_folder_path, yaml_file)
       
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)

        plugin_name = yaml_file[:-5]
        description = data.get('description', 'No description available')
        enabled_status = data.get('enabled', 'No enabled status available')
        example = data.get('examples', 'No example available')
        custom_modification= data.get('custom_modification', False)
        plugin_Status= data.get('isdeleted',False)
        Endpoint = data["configurations"].get('endpoint_url', 'No Endpoint available')
        DEPLOYMENT_NAME= data["configurations"].get('deployment_name', 'No deployment name available')
        

        # Extract parameter descriptions and return descriptions
        parameter_description = ""
        if 'parameters' in data:
            parameter_description = "; ".join([f"{param['name']} ({param['type']}): {param.get('description', 'No description')}" for param in data['parameters']])
        return_description = ""
        if 'returns' in data:
            return_description = "; ".join([f"{ret['name']} ({ret['type']}): {ret.get('description', 'No description')}" for ret in data['returns']])
 
        # Add plugin details to the plugins list
        plugin_info = {
            "plugin_name": plugin_name,
            "description": description,
            "example": example,
            "parameter_description": parameter_description,
            "return_description": return_description,
            "enabled_status": enabled_status,
            "custom_modification": custom_modification,
            "Endpoint":Endpoint,
            "DEPLOYMENT_NAME": DEPLOYMENT_NAME,
            "Is_deleted" : plugin_Status
        }
        plugins.append(plugin_info)


        # Check for updates to the existing record
        if plugin_name in existing_plugins:
            existing_plugin = existing_plugins[plugin_name]
            if (existing_plugin['description'] != description or
                existing_plugin['enabled_status'] != enabled_status or
                existing_plugin['example'] != example):
                # Update the specific row with new details
                existing_plugins[plugin_name] = plugin_info
        else:
            # Add new plugin if it does not exist in CSV
            existing_plugins[plugin_name] = plugin_info
    # Write the updated details back to the CSV file
    with open(csv_file_path, mode='w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=[
            "plugin_name", "description", "example", "parameter_description",
            "return_description", "enabled_status" ,"custom_modification",
        "Endpoint", "DEPLOYMENT_NAME","Is_deleted"
        ])
        writer.writeheader()
        # print(existing_plugins.values())
        # Write all plugins, including modified rows, back to the CSV
        for plugin in existing_plugins.values():
            print(plugin)
            writer.writerow(plugin)
   
    # return plugins
    return JsonResponse(plugins ,safe=False)

@api_view(['GET'])
def list_adminplugins(request):

    """
    Retrieves a list of plugins names from the admin plugins folder
    Returns:
         A list of dictionaries, each containing:
            `plugin_name` (str): Name of the plugin file without extension
    """ 
    plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'adminplugins'))
    yaml_files = [f for f in os.listdir(plugins_folder_path) if f.endswith('.yaml') and os.path.isfile(os.path.join(plugins_folder_path, f))]
    plugins=[]
    for yaml_file in yaml_files:
        plugin_name = yaml_file[:-5]
        plugin_info = {
            "plugin_name": plugin_name,
        }
        plugins.append(plugin_info)
    return JsonResponse(plugins ,safe=False)

@api_view(['GET'])
def list_draftplugins(request):

    """
    Retrieves a list of plugins from the plugins folder, including their names,
    descriptions, examples, parameters, return values, and enabled statuses.
   
    This function reads each `.yaml` file in the plugins folder and extracts
    details such as `plugin_name`, `description`, `example`, `parameters`,
    `return values`, and `enabled_status`. If a field is missing, it provides a
    default message.
   
    Returns:
        A list of dictionaries, each containing:
        - `plugin_name` (str): Name of the plugin file without extension
        - `description` (str): Plugin description or a default message
        - `example` (str): Example usage of the function
        - `parameter_description` (str): Description of parameters
        - `return_description` (str): Description of return values
        - `enabled_status` (str): Enabled status
    """ 
    plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'draftplugins'))
 
    # Get all .yaml files from the plugins folder
    yaml_files = [f for f in os.listdir(plugins_folder_path) if f.endswith('.yaml') and os.path.isfile(os.path.join(plugins_folder_path, f))]
    plugins = []
    for yaml_file in yaml_files:
        file_path = os.path.join(plugins_folder_path, yaml_file)
       
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)

        plugin_name = yaml_file[:-5]
        description = data.get('description', 'No description available')
        enabled_status = data.get('enabled', 'No enabled status available')
        example = data.get('examples', 'No example available')
        custom_modification= data.get('custom_modification', False)
        plugin_Status= data.get('isdeleted',False)
        Endpoint = data["configurations"].get('endpoint_url', 'No Endpoint available')
        DEPLOYMENT_NAME= data["configurations"].get('deployment_name', 'No deployment name available')
        

        # Extract parameter descriptions and return descriptions
        parameter_description = ""
        if 'parameters' in data:
            parameter_description = "; ".join([f"{param['name']} ({param['type']}): {param.get('description', 'No description')}" for param in data['parameters']])
        return_description = ""
        if 'returns' in data:
            return_description = "; ".join([f"{ret['name']} ({ret['type']}): {ret.get('description', 'No description')}" for ret in data['returns']])
 
        # Add plugin details to the plugins list
        plugin_info = {
            "plugin_name": plugin_name,
            "description": description,
            "example": example,
            "parameter_description": parameter_description,
            "return_description": return_description,
            "enabled_status": enabled_status,
            "custom_modification": custom_modification,
            "Endpoint":Endpoint,
            "DEPLOYMENT_NAME": DEPLOYMENT_NAME,
            "Is_deleted" : plugin_Status
        }
        plugins.append(plugin_info)
    return JsonResponse(plugins ,safe=False)

@api_view(['POST'])
def plugin_enable(request):
    data= request.data
    plugin_name=data.get('plugin_name')
    plugin_state=data.get('state')
    print(plugin_state)
    if not plugin_name:
        return HttpResponse("Plugin name is required.", content_type="text/plain", status=status.HTTP_400_BAD_REQUEST)
     # Define the relative path to the plugins folder
    # plugins_folder_path =
    plugins_folder =  os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
 
    yaml_file = os.path.join(plugins_folder, plugin_name) + ".yaml"
   
    # Ensure the file exists
    if not os.path.exists(yaml_file):
        return HttpResponse(f"YAML file for plugin '{plugin_name}' not found.", content_type="text/plain", status=status.HTTP_404_NOT_FOUND)
    # # Load the YAML file
    # with open(yaml_file , 'r') as file:
    #     data = yaml.safe_load(file)
    # # Modify the YAML data
   
   
    # Load the YAML file with ruamel.yaml
    yaml = YAML()
    yaml.preserve_quotes = True  # Ensure quotes in the original file are preserved
    with open(yaml_file, 'r') as file:
        config = yaml.load(file)
   
    # Modify the 'enabled' property based on the state
        config['enabled'] = bool(plugin_state)
        print(config['enabled'])
    # Save the modified YAML data back to the file without altering its structure
    with open(yaml_file, 'w') as file:
        yaml.dump(config, file)
 
    responce_text="YAML file updated successfully."
    return  HttpResponse (responce_text, content_type="text/plain", status= status.HTTP_200_OK)


@api_view(['GET'])
def list_llm_models(request):
    
    # Fetch only the 'name' column from all LLMModel entries
    model_names =APIDetails.objects.values()
    models_name_list=list(model_names)
    
    return JsonResponse (models_name_list, safe=False )


@api_view(['POST'])
def llmconfig(request):
    # Get the model name from the request body
    data= request.data
    deployment_model=data.get('deployment_model')
 
    
    api_details =APIDetails.objects.filter(deployment_model=deployment_model).values().first()
    config_file_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'taskweaver_config.json'))
    
    
      # Check if there's an API detail available
    if api_details:
        # Create the configuration dictionary in the specified format        
        config = {
        "llm.api_base": api_details['api_endpoint'],
        "llm.api_type": api_details['api_type'],
        "llm.model": api_details['deployment_model'],
        "llm.response_format": api_details['response_format'],
        "llm.azure.api_version": api_details['api_version'],
        "llm.past_messages": api_details['past_messages'],
        "llm.max_tokens": api_details['max_tokens'],
        "llm.temperature": api_details['temperature'],
        "llm.top_p": api_details['top_p'],
        "llm.frequency_penalty": api_details['frequency_penalty'],
        "llm.presence_penalty": api_details['presence_penalty'],
        "llm.stop": api_details['stop'],
        "llm.stream": api_details['stream'],
        "llm.azure_ad.aad_auth_mode": "default_azure_credential",
        "execution_service.kernel_mode": "local"  # Custom field
    }
        #  Write the config data to the JSON file
        with open(config_file_path, 'w') as file:
            json.dump(config, file, indent=4)

    responce_text="taskweaver_config.json updated successfully."
    return  HttpResponse (responce_text, content_type="text/plain", status= status.HTTP_200_OK)



@api_view(['POST'])
def create_api_details(request):
    serializer = APIDetailsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()  # Save the validated data to the APIDetails model
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['POST'])
def update_api_details(request):
    id = request.data.get('id')

    # Check if id is provided
    if not id:
        return Response({"error": "id is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the APIDetails instance by id
        api_details = APIDetails.objects.get(id=id)
    except APIDetails.DoesNotExist:
        return Response({"error": "APIDetails with the given id does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    # Deserialize and validate the request data
    serializer = APIDetailsSerializer(api_details, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()  # Save the updates to the database
        return Response(serializer.data, status=status.HTTP_200_OK)
    # Return errors if validation fails
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





def update_csv_file(plugin_name, updates):
    """Update the CSV file with plugin details based on the provided updates."""
    plugins_folder = os.path.abspath(os.path.join(os.getcwd(), '.'))
    csv_file_path = os.path.join(plugins_folder, 'plugins.csv')
    
    # Load CSV file if it exists, otherwise create a new DataFrame
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        
    
    endpoint = updates.get('endpoint_url', 'default_endpoint')
    deployment_name = updates.get('deployment_name', 'default_deployment_name')

    
    # # Check if the plugin already exists in the CSV
    if plugin_name in df['plugin_name'].values:
        index = df[df['plugin_name'] == plugin_name].index
        if not index.empty:
            df.at[index[0], 'Endpoint'] = endpoint
            df.at[index[0], 'DEPLOYMENT_NAME'] = deployment_name
    # Save the DataFrame back to the CSV file
    df.to_csv(csv_file_path, index=False)


def update_python_file(plugin_name, updates):
    """Update the Python file variables based on the provided updates."""
    plugins_folder = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
    python_file_path = os.path.join(plugins_folder, plugin_name) + ".py"
    
    if os.path.exists(python_file_path):
        with open(python_file_path, 'r') as file:
            code = file.read()
        
        # Parse the code into an Abstract Syntax Tree (AST)
        tree = ast.parse(code)
        
        # Replace the variables in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):  # Look for assignment statements
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in updates:
                        # Replace the variable with the new value
                        new_value = updates[target.id]
                        # Convert the new value into a valid AST node
                        value_node = ast.Constant(value=new_value)
                        node.value = value_node  # Update the assignment with new value
        
        # Convert the updated AST back to source code
        updated_code = ast.unparse(tree)
        
        # Save the updated code back to the Python file
        with open(python_file_path, 'w') as file:
            file.write(updated_code)
    else:
        print(f"Python file not found: {python_file_path}")

@api_view(['POST'])
def update_files(request):
    """Update the YAML file and Python file based on the provided JSON string."""
    data = request.data
    plugin_name = data.get('name')
    updates = data
    
    # Update YAML and Python files
    update_csv_file(plugin_name, updates)
    # update_python_file(plugin_name, updates)
    update_YAML_files(plugin_name,updates)
    
    response_text = "CSV and Python files updated successfully."
    return HttpResponse(response_text, content_type="text/plain", status=status.HTTP_200_OK)



@api_view(['GET'])
def configfile(request):
    
    config_file_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'taskweaver_config.json'))
    
    # Read current JSON file content and update the model name
    with open(config_file_path, 'r') as file:
        config = json.load(file)
    return JsonResponse (config, safe=False)


@api_view(['GET'])
def get_yaml_files_with_key_value(request):

    # Usage example
    plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
    target_key = 'custom_modification'

    matching_files = []
    
    # Iterate through all files in the directory
    for filename in os.listdir(plugins_folder_path):
        if filename.endswith(".yaml"):
            file_path = os.path.join(plugins_folder_path, filename)
            try:
                # Load YAML file
                with open(file_path, 'r') as file:
                    data = yaml.safe_load(file)
                    
                    # Check if the key exists and its value is True
                    if data.get(target_key) is True:
                        matching_files.append(filename[:-5])
            
            except yaml.YAMLError as e:
                print(f"Error reading {filename}: {e}")
            except Exception as e:
                print(f"Unexpected error with {filename}: {e}")
    # print(matching_files,type(matching_files))
    return JsonResponse (matching_files, safe=False )


@api_view(['POST'])
def create_session(request):
    try:
        code_executor.set_plugin_folder("plugins")
        set_plugin_folder("plugins")
        global user_session_id
        global app_session_dict
        global session
        user_session_id = request.data['user']
        app_session_dict[user_session_id] = app.get_session()
        session=app_session_dict[user_session_id]
        session_cwd_path = session.execution_cwd
        session.event_emitter
        return Response({'session_id': session.session_id, 'status': 'Session created successfully'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def create_draftplugin_session(request):
    try:
        code_executor.set_plugin_folder("draftplugins")
        set_plugin_folder("draftplugins")
        global  draft_session_id
        global draft_session_dict
        global draftsession
        draft_session_id = request.data['user']
        draft_session_dict[draft_session_id] = draftapp.get_session()
        draftsession=draft_session_dict[draft_session_id]
        draftsession_cwd_path = draftsession.execution_cwd
        draftsession.event_emitter
        return Response({'session_id': draftsession.session_id, 'status': 'Session created successfully'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
 

@api_view(['POST'])
def create_admin_session(request):
    try:
        code_executor.set_plugin_folder("adminplugins")
        set_plugin_folder("adminplugins")
        global admin_session_id 
        global admin_session_dict
        global adminsession 
        
        admin_session_id = request.data['user']
        admin_session_dict[admin_session_id] = adminapp.get_session()
        adminsession=admin_session_dict[admin_session_id]
        
        adminsession_cwd_path = adminsession.execution_cwd
        adminsession.event_emitter
        return Response({'session_id': adminsession.session_id, 'status': 'Admin Session created successfully'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
 

def update_YAML_files(plugin_name, updates):
    """Update the YAML file  based on the provided JSON string."""

    plugins_folder =  os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
    yaml_file_path = os.path.join(plugins_folder, plugin_name) + ".yaml"
    # Convert JSON string to a dictionary
    endpoint = updates.get('endpoint', 'default_endpoint')
    deployment_name = updates.get('deployment', 'default_deployment_name')
    # Modifying the payloads data
    payload_updates = {
        "endpoint_url" : endpoint,
        "deployment_name" : deployment_name
    }

    # Update YAML file
    if os.path.exists(yaml_file_path):
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
            # print(data)
        
        # Update data with matching keys from the updates dictionary
        for key, value in payload_updates.items():
            if key in data["configurations"]:
                # data[key] = value
                data["configurations"][key]= value
            else:
                print(f"Key '{key}' not found in the YAML file.")
        # Save the updated data back to the YAML file
        with open(yaml_file_path, 'w') as file:
            yaml.safe_dump(data, file)
        
        print("YAML file updated successfully!")
    else:
        print(f"YAML file not found: {yaml_file_path}")



class ConsoleEventHandler(SessionEventHandler):
    def handle(self, event: TaskWeaverEvent):
        print(event.t, event.msg)
@api_view(['POST'])
def SendMessage(request):
    global session
    encoded_blob=''
    img_path=''
    data_url=''
    mime_type=''
    file_name=''
    user_msg_content=''
    serializer = BlobDataSerializer(data=request.data)
    prompt=request.data["prompt"] 
    if serializer.is_valid():
        encoded_blob = serializer.validated_data['blob_data']
        File_name = serializer.validated_data['File_name']
        try:
            decoded_data =base64.b64decode(encoded_blob)
            file_path = os.path.join('..', 'Temp_file', File_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(decoded_data)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        file_path=os.path.realpath("../Temp_file/"+File_name)
        files_to_send = [{
            "name": File_name,
            "path": file_path
        }] 
    try:
        if serializer.is_valid():
            res= session.send_message(message=prompt,event_handler=ConsoleEventHandler(),files = files_to_send)
        elif prompt:
            res= session.send_message(message=prompt,event_handler=ConsoleEventHandler())
        artifact_paths = [
            p
            for p in res.post_list
            for a in p.attachment_list
            if a.type == AttachmentType.artifact_paths
            for p in a.content
        ]
        session_cwd_path = session.execution_cwd
        print(session_cwd_path)
        session.event_emitter
        # print(res.post_list)
        for post in [p for p in res.post_list if p.send_to == "User"]:
            files: List[Tuple[str, str]] = []
            if len(artifact_paths) > 0:
                for file_path in artifact_paths:
                    img_path=file_path
                    file_name = os.path.basename(file_path)
                    files.append((file_name, file_path))

            # Extract the file path from the message and display it
            user_msg_content = post.message
            pattern = r"(!?)\[(.*?)\]\((.*?)\)"
            matches = re.findall(pattern, user_msg_content)
            for match in matches:
                img_prefix, file_name, file_path = match
                if(img_path==''):
                    img_path=session_cwd_path+"\\"+file_path
                files.append((file_name, file_path))
                user_msg_content = user_msg_content.replace(
                    f"{img_prefix}[{file_name}]({file_path})",
                    file_name,
                )
                with open(img_path, 'rb') as file: 
                    file_data = file.read()
                encoded_blob = base64.b64encode(file_data).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(img_path)
                data_url = f'data:{mime_type};base64,{encoded_blob}'
        
    except Exception as e:
        return Response({'error': str(e)})
    return JsonResponse({'content':user_msg_content,'encoded_blob':data_url,'file_type':mime_type,'file_name':file_name},safe=False)

@api_view(['POST'])
def draftPluginSendMessage(request):
    global draftsession
    encoded_blob=''
    img_path=''
    data_url=''
    mime_type=''
    file_name=''
    user_msg_content=''
    serializer = BlobDataSerializer(data=request.data)
    prompt=request.data["prompt"] 
    if serializer.is_valid():
        encoded_blob = serializer.validated_data['blob_data']
        File_name = serializer.validated_data['File_name']
        try:
            decoded_data =base64.b64decode(encoded_blob)
            file_path = os.path.join('..', 'Temp_file', File_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(decoded_data)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        file_path=os.path.realpath("../Temp_file/"+File_name)
        files_to_send = [{
            "name": File_name,
            "path": file_path
        }] 
    try:
        if serializer.is_valid():
            res= draftsession.send_message(message=prompt,event_handler=ConsoleEventHandler(),files = files_to_send)
        elif prompt:
            res= draftsession.send_message(message=prompt,event_handler=ConsoleEventHandler())
        artifact_paths = [
            p
            for p in res.post_list
            for a in p.attachment_list
            if a.type == AttachmentType.artifact_paths
            for p in a.content
        ]
        draftsession_cwd_path = draftsession.execution_cwd
        print(draftsession_cwd_path)
        draftsession.event_emitter
        # print(res.post_list)
        for post in [p for p in res.post_list if p.send_to == "User"]:
            files: List[Tuple[str, str]] = []
            if len(artifact_paths) > 0:
                for file_path in artifact_paths:
                    img_path=file_path
                    file_name = os.path.basename(file_path)
                    files.append((file_name, file_path))

            # Extract the file path from the message and display it
            user_msg_content = post.message
            pattern = r"(!?)\[(.*?)\]\((.*?)\)"
            matches = re.findall(pattern, user_msg_content)
            for match in matches:
                img_prefix, file_name, file_path = match
                if(img_path==''):
                    img_path=draftsession_cwd_path+"\\"+file_path
                files.append((file_name, file_path))
                user_msg_content = user_msg_content.replace(
                    f"{img_prefix}[{file_name}]({file_path})",
                    file_name,
                )
                with open(img_path, 'rb') as file: 
                    file_data = file.read()
                encoded_blob = base64.b64encode(file_data).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(img_path)
                data_url = f'data:{mime_type};base64,{encoded_blob}'
        
    except Exception as e:
        return Response({'error': str(e)})
    return JsonResponse({'content':user_msg_content,'encoded_blob':data_url,'file_type':mime_type,'file_name':file_name},safe=False)



@api_view(['POST'])
def adminSendMessage(request):
    global adminsession
    global yaml_code_content
    global python_code_content
    global plugin_name
    global plugin_description
    encoded_blob=''
    img_path=''
    data_url=''
    mime_type=''
    file_name=''
    user_msg_content=''
    serializer = BlobDataSerializer(data=request.data)
    prompt=request.data["prompt"] 
    if serializer.is_valid():
        encoded_blob = serializer.validated_data['blob_data']
        File_name = serializer.validated_data['File_name']
        try:
            decoded_data =base64.b64decode(encoded_blob)
            file_path = os.path.join('..', 'Temp_file', File_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(decoded_data)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        file_path=os.path.realpath("../Temp_file/"+File_name)
        files_to_send = [{
            "name": File_name,
            "path": file_path
        }] 
    try:
        if serializer.is_valid():
            res= adminsession.send_message(message=prompt,event_handler=None,files = files_to_send)
        elif prompt:
            res= adminsession.send_message(message=prompt)
        artifact_paths = [
            p
            for p in res.post_list
            for a in p.attachment_list
            if a.type == AttachmentType.artifact_paths
            for p in a.content
        ]
        adminsession_cwd_path = adminsession.execution_cwd
        adminsession.event_emitter
        print(res.post_list)
        for post in [p for p in res.post_list if p.send_to == "User"]:
            files: List[Tuple[str, str]] = []
            if len(artifact_paths) > 0:
                for file_path in artifact_paths:
                    img_path=file_path
                    file_name = os.path.basename(file_path)
                    files.append((file_name, file_path))

            # Extract the file path from the message and display it
            user_msg_content = post.message
        #     pattern = r"(!?)\[(.*?)\]\((.*?)\)"
        #     matches = re.findall(pattern, user_msg_content)
        #     for match in matches:
        #         img_prefix, file_name, file_path = match
        #         if(img_path==''):
        #             img_path=adminsession_cwd_path+"\\"+file_path
        #         files.append((file_name, file_path))
        #         user_msg_content = user_msg_content.replace(
        #             f"{img_prefix}[{file_name}]({file_path})",
        #             file_name,
        #         )
        #         with open(img_path, 'rb') as file: 
        #             file_data = file.read()
        #         encoded_blob = base64.b64encode(file_data).decode('utf-8')
        #         mime_type, _ = mimetypes.guess_type(img_path)
        #         data_url = f'data:{mime_type};base64,{encoded_blob}'
        python_pattern = r'```python\n(.*?)```'
        yaml_pattern = r'```yaml\n(.*?)```'
        python_code = re.search(python_pattern, user_msg_content, re.DOTALL)
        yaml_code = re.search(yaml_pattern, user_msg_content, re.DOTALL)
        print(plugin_name in user_msg_content)
        print("successfully created" in user_msg_content)
        print(os.path.realpath("../project/"))
        if(python_code_content==""):
            python_code_content = python_code.group(1).strip() if python_code else ""
            yaml_code_content = yaml_code.group(1).strip() if yaml_code else ""
            if(yaml_code_content!=""):
                match=re.search(r'(plugin_name|name):\s*(\S+)', yaml_code_content)
                plugin_description_match=re.search(r'(plugin_description|description):\s*(\S+)', yaml_code_content)
                if match:
                    plugin_name = match.group(2)
                    print(plugin_name)
                if plugin_description_match:
                    plugin_description = plugin_description_match.group(2)
                    print(plugin_description)
        elif ((plugin_name in user_msg_content or "new plugin" in user_msg_content) and "success" in user_msg_content and ("saved" in user_msg_content or "created" in user_msg_content or "submit" in user_msg_content)):
            print("IN")
            print(os.path.realpath("../project/draftplugins"))
            with open(os.path.realpath("../project/draftplugins")+"/"+plugin_name+".py","w") as py_file:
                py_file.write(python_code_content)
            with open(os.path.realpath("../project/draftplugins")+"/"+plugin_name+".yaml", "w") as yaml_file:
                yaml_file.write(yaml_code_content)
            generate_intent_catalog(plugin_name,plugin_description)
            yaml_code_content=""
            python_code_content=""
            plugin_name=""
            plugin_description=""

    except Exception as e:
        return Response({'error': str(e)})
    return JsonResponse({'content':user_msg_content,'encoded_blob':data_url,'file_type':mime_type,'file_name':file_name},safe=False)


@api_view(['POST'])
def Delete_plugin(request):
    Pulgin_delete=request.data.get('plugin_name')
    plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
    pulgin_name=f"{Pulgin_delete}.yaml"
    # target_key = 'isdeleted'
    if not Pulgin_delete:
            return Response({"error": "Filename is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    file_path = os.path.join(plugins_folder_path, pulgin_name)
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return Response({"error": f"File {file_path} not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Load YAML file
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            
        # Update the target key
        data["isdeleted"]= True
        data["enabled"]= False
        # Save the updated data back to the YAML file
        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file, indent=4)
    except Exception as e:
        print(f"Unexpected error with {pulgin_name}: {e}")
    except yaml.YAMLError as e:
        print(f"Error reading {pulgin_name}: {e}")
    return JsonResponse (data,safe=False )

@api_view(['POST'])
def approvePlugin(request):
    Pulgin_delete=request.data.get('plugin_name')
    approve_plugin=request.data.get('approve')
    plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'draftplugins'))
    pulgin_name=f"{Pulgin_delete}.yaml"
    py_name=f"{Pulgin_delete}.py"
    # target_key = 'isdeleted'
    if not Pulgin_delete:
            return Response({"error": "Filename is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    file_path = os.path.join(plugins_folder_path, pulgin_name)
    py_file_path=os.path.join(plugins_folder_path, py_name)
    target_plugins_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'plugins'))
    yaml_target_path=os.path.join(target_plugins_folder_path, pulgin_name)
    py_target_path=os.path.join(target_plugins_folder_path, py_name)
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return Response({"error": f"File {file_path} not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Load YAML file
        if approve_plugin=="Approve":
            shutil.copyfile(file_path, yaml_target_path)
            shutil.copyfile(py_file_path, py_target_path)
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            
        # Update the target key
        data["isdeleted"]= True
        data["enabled"]= False
        # Save the updated data back to the YAML file
        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file, indent=4)
    except Exception as e:
        print(f"Unexpected error with {pulgin_name}: {e}")
    except yaml.YAMLError as e:
        print(f"Error reading {pulgin_name}: {e}")
    return JsonResponse (data,safe=False )


@api_view(['POST'])
def update_packges(request):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            print(data)
            # Validate input
            if not isinstance(data, list) or not all("name" in pkg for pkg in data):
                return JsonResponse({"error": "Invalid data format. Expected a list of {'name': ..., 'version': ... (optional)}."}, status=400)
            
            # Define file path for the CSV file
            file_path = os.path.abspath(os.path.join(os.getcwd(), '..','requirements.txt'))
            # Ensure the file exists before appending
            if not os.path.exists(file_path):
                open(file_path, "w").close()

            # Read existing data to avoid duplicates
            with open(file_path, mode="r") as file:
                existing_lines = {line.strip() for line in file.readlines()}

            # Prepare new lines to append
            new_lines = []
            for package in data:
                name = package["name"]
                version = package.get("version", None)
                line = f"{name}>={version}" if version else name
                if line not in existing_lines:  # Avoid duplicate entries
                    new_lines.append(line)

            # Append new lines to the file
            with open(file_path, mode="a") as file:
                for line in new_lines:
                    file.write(f"{line}\n")

            return JsonResponse({"message": "requirements.txt updated successfully", "file_path": file_path})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

def generate_intent_catalog(plugin_name,plugin_description):
    # Load configuration from the file
    config_file_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'project', 'taskweaver_config.json'))
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except Exception as e:
        return JsonResponse({"error": f"Failed to load configuration: {str(e)}"}, status=500)

    # Extract necessary values from the config
    api_base = config.get("llm.api_base")
    api_version = config.get("llm.azure.api_version")
    model_name = config.get("llm.model")
    api_type = config.get("llm.api_type")

    # Ensure parameters are valid numbers or set defaults
    try:
        temperature = float(config.get("llm.temperature", 0.7))
        top_p = float(config.get("llm.top_p", 1.0))
        frequency_penalty = float(config.get("llm.frequency_penalty", 0.0))
        presence_penalty = float(config.get("llm.presence_penalty", 0.0))
    except ValueError as e:
        return JsonResponse({"error": f"Invalid parameter value: {str(e)}"}, status=400)

    # Authenticate using DefaultAzureCredential
    try:
        
        credential = DefaultAzureCredential()

            # Prepare the prompt for LLM
        prompt = f"""
            Generate 20 possible intents for the given plugin. Only provide the intent names.

            Plugin Name: {plugin_name}
            Plugin Description: {plugin_description}
            """
        
        
        # Create the AzureChatOpenAI client
        client = AzureChatOpenAI(
            azure_endpoint=api_base,
            openai_api_version=api_version,
            deployment_name=model_name,
            openai_api_type=api_type,
            azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )

      
        response = client(prompt)
        
        
        intents=response.content.strip().split('\n')        
        intent_string="\n".join(intents)
        intent_file_path = os.path.abspath(os.path.join(os.getcwd(), '..', 
                                'project', 'Essential_Documents','intent_routing','Intent catalogue.csv'))
        
        
        
        with open(intent_file_path ,'a', newline='', encoding='utf-8') as intent_file:
            intent_file.write(f"{plugin_name},\"{intent_string}\"\n")

        return JsonResponse({"response": intents}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

