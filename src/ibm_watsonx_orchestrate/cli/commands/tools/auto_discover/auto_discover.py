import ast
from enum import Enum
import re
import tempfile
from typing import Optional
from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.client.autodiscover import BaseInferenceClient,AIGatewayClient, WatsonxAIClient, MLProxyClient, GroqClient
from ibm_watsonx_orchestrate.utils.environment import EnvService

TOOL_MODULE = "ibm_watsonx_orchestrate.agent_builder.tools"
TOOL_DECORATOR_NAME = "tool"


WXAI_URL_ENV_KEY = "WATSONX_URL"
WXAI_SPACE_ID_ENV_KEY = "WATSONX_SPACE_ID"
WXAI_APIKEY_ENV_KEY = "WATSONX_APIKEY"

WXO_INSTANCE_ENV_KEY = "WO_INSTANCE"
WXO_APIKEY_ENV_KEY = "WO_API_KEY"

GROQ_APIKEY_ENV_KEY = "GROQ_API_KEY"

AUTO_DISCOVER_TOOL_INSRUCTIONS = """
You are an expert software engineer, tasked to analyze and describe python functions.
Without attempting to execute any code, you should analyze the provided python function to determine the intended functionality
as well as the purpose and type of any of the functions parameters or return values.

Use the information from this analysis to generate an appropriate description in google python docstring format.
It is very important that this conforms exactly to the google python docstring format!

The docstring should contain a maximum of three sections;
 - A description of the function
 - Args: descriptions and type annotations for each of the paramaters of the function (if any)
 - Returns: description and type annotation for the return value of the function (if any)

The docstring should be enclosed with three double quote characters on separate lines, before and after the docstring

The docstring should only describe the function requested

Here is an example:
\"\"\"    
Mock Docstring Description

Args:
  Mock Docstring Args

Returns:
  Mock Docstring Results
\"\"\"

Your reply should consist only of the generated docstring with no comments, annotations or summaries
"""


def create_auto_discover_tool_prompt(function_name: str, file_code: str):
  return f"""
Analyze and produce a docstring for the function \"{function_name}\" in the following python code:

{file_code}

  """


def auto_discover_python_tools(
    file: str, 
    output_file: Optional[str] = None, 
    env_file: Optional[str] = None, 
    llm: Optional[str] = None,
    function_names: Optional[list[str]] = None
  ) -> str:

  full_python_file = open(file).read()
  file_tree = ast.parse(full_python_file)

  for node in ast.walk(file_tree):
    for child in ast.iter_child_nodes(node):
      child.parent = node

  parser = AutoDiscoverToolParser(
    llm=llm,
    function_names=function_names,
    full_python_file=full_python_file,
    env_file=env_file
  )

  new_tree = parser.visit(file_tree)

  new_contents = ast.unparse(new_tree)
  new_contents_lines = new_contents.splitlines(keepends=True)

  if not parser.has_tool_import:
    new_contents_lines.insert(0,f"from {TOOL_MODULE} import {TOOL_DECORATOR_NAME}\n")

  if output_file:
    open(output_file,"w+").writelines(new_contents_lines)
  else:
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", suffix=".py", delete=False) as f:
      f.writelines(new_contents_lines)
      output_file = f"{f.name}"

  return output_file
  

def create_docstring_node(docstring: str):
  return ast.Expr(ast.Constant(docstring))

def get_decorator_name(decorator):
  if isinstance(decorator, ast.Call):
    decorator = decorator.func

  if isinstance(decorator, ast.Attribute):
    name = decorator.attr
  else:
    name = decorator.id
  
  return name

def get_env(env_file: str = None) -> dict:
  env_svc = EnvService(Config())
  default_env = env_svc.get_default_env_file()
  return EnvService.merge_env(default_env_path=default_env, user_env_path=env_file)

class InferenceProvider(str,Enum):
  GATEWAY = "ai-gateway"
  WXAI = "watsonx-ai"
  PROXY = "ml-proxy"
  GROQ = "groq"

def _infer_inference_provider_from_model(selected_model: str) -> InferenceProvider | None:
  
  if selected_model:

    if selected_model.startswith("virtual-model") or selected_model.startswith("virtual-policy"):
      return [ InferenceProvider.GATEWAY ]
    
    if selected_model.startswith("watsonx"):
      return [ InferenceProvider.WXAI, InferenceProvider.PROXY ]

    if selected_model.startswith("groq"):
      return [ InferenceProvider.GROQ, InferenceProvider.PROXY ]
      
  return [ InferenceProvider.WXAI, InferenceProvider.GROQ, InferenceProvider.PROXY ]

def _select_inference_provider_from_env(available_providers: list[InferenceProvider], env: dict) -> InferenceProvider:

  if InferenceProvider.GATEWAY in available_providers:
    return InferenceProvider.GATEWAY

  groq_api_key = env.get(GROQ_APIKEY_ENV_KEY, None)
  if groq_api_key and InferenceProvider.GROQ in available_providers:
    return InferenceProvider.GROQ
  
  wxai_api_key, wxai_space_id = env.get(WXAI_APIKEY_ENV_KEY, None), env.get(WXAI_SPACE_ID_ENV_KEY, None)
  if wxai_api_key and wxai_space_id and InferenceProvider.WXAI in available_providers:
    return InferenceProvider.WXAI
  
  wxo_api_key, wxo_instance_url = env.get(WXO_APIKEY_ENV_KEY, None), env.get(WXO_INSTANCE_ENV_KEY)
  if wxo_api_key and wxo_instance_url and InferenceProvider.PROXY in available_providers:
    return InferenceProvider.PROXY
  
  
  raise ValueError(f"No inference provider available for auto-discover call")


def get_inference_client(selected_model: str = None, env_file: str = None) -> BaseInferenceClient:

  env = get_env(env_file=env_file)
  
  possible_providers = _infer_inference_provider_from_model(selected_model)

  if selected_model:
    
    if selected_model.startswith("groq/"):
      selected_model = selected_model.removeprefix("groq/")
      
    elif selected_model.startswith("watsonx/"):
      selected_model = selected_model.removeprefix("watsonx/")

  provider = _select_inference_provider_from_env(available_providers=possible_providers, env=env)

  match provider:

    case InferenceProvider.GATEWAY:

      return AIGatewayClient(
        env=env,
        model=selected_model
      )
    
    case InferenceProvider.GROQ: 

      groq_api_key = env.get(GROQ_APIKEY_ENV_KEY, None)
      return GroqClient(
        api_key=groq_api_key,
        model=selected_model
      )
    
    case InferenceProvider.WXAI:

      wxai_api_key, wxai_space_id = env.get(WXAI_APIKEY_ENV_KEY, None), env.get(WXAI_SPACE_ID_ENV_KEY, None)
      return WatsonxAIClient(
        api_key=wxai_api_key,
        space_id=wxai_space_id,
        env=env,
        model=selected_model
      )
    
    case InferenceProvider.PROXY:  

      wxo_api_key, wxo_instance_url = env.get(WXO_APIKEY_ENV_KEY, None), env.get(WXO_INSTANCE_ENV_KEY)
      return MLProxyClient(
        api_key=wxo_api_key,
        base_url=wxo_instance_url,
        env=env,
        model=selected_model
      )
    
    case _:
      raise ValueError(f"Invalid inference provider for autodiscover call")
  

def extract_content_from_docstring(docstr):
  regex = re.compile("[\"']{3}((.|\\n|\\r)*)[\"']{3}", re.MULTILINE)
  match = regex.match(docstr)
  if match:
    return match.group(1)
    

class AutoDiscoverToolParser(ast.NodeTransformer):

  def __init__(self, full_python_file: str, env_file: str = None, llm: Optional[str] = None, function_names: Optional[list[str]] = None):
    self.__response_client = get_inference_client(selected_model=llm,env_file=env_file)
    self.__function_names = function_names
    self.has_tool_import = False
    self.full_python_file = full_python_file

  def visit_ImportFrom(self, node):
    if node.module == TOOL_MODULE:
      if TOOL_DECORATOR_NAME in [n.name for n in node.names]:
        self.has_tool_import = True
    return node

  def visit_FunctionDef(self, node):
    if not isinstance(node.parent, ast.Module):
      return node
    
    if self.__function_names and node.name not in self.__function_names:
      return node

    docstring = ast.get_docstring(node)

    if docstring is None:
      # create request
      auto_discover_prompt = create_auto_discover_tool_prompt(node.name,self.full_python_file)

      # invoke ai_gateway/wxai to generate docstring

      ai_response = self.__response_client.generate_response(
        input=auto_discover_prompt,
        instructions=AUTO_DISCOVER_TOOL_INSRUCTIONS
      )

      content = self.__response_client.extract_message_from_response(
        ai_response
      )

      docstring = extract_content_from_docstring(content)

      # convert to ast node
      docstring_node = create_docstring_node(docstring)

      # inject docstring into function tree
      node.body.insert(0, docstring_node)
    
    if TOOL_DECORATOR_NAME not in [get_decorator_name(n) for n in node.decorator_list]:
      node.decorator_list.append(ast.Call(func=ast.Name(TOOL_DECORATOR_NAME), args=[], keywords=[]))

    return node