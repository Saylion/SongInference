import gradio as gr
import os
import numpy as np
import time
import shutil as sh
from tqdm import tqdm

drive_path = '/content/drive/MyDrive/RVC'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')


def raise_exception(msg, type):
  if type == 'err':
    return gr.Error(msg)
  elif type == 'warn':
    return gr.Warning(msg)
  elif type == 'info':
    return gr.Info(msg)

def display_progress(message, percent, progress=None):
  progress(percent, desc=message)

def scan_model(progress=gr.Progress()):
  display_progress("Preparing...", 0, progress)
  if not os.path.exists(drive_path):
    err_msg = f"{drive_path} not found"
    raise_exception(err_msg, 'err')

  folders = os.listdir(drive_path)
  array_folders = []
  array_final_folders = []
  for folder in folders:
    if not os.path.isfile(os.path.join(drive_path, folder)):
      array_folders.append(folder)
      list_folder = np.array(array_folders)
  index = ['weights', '.ipynb_checkpoints']
  list_folder = np.setdiff1d(list_folder, index)
  list_folder.sort()
  
  with tqdm(range(100), total=len(list_folder), desc='Scanning available model...', unit=' folder') as pbar:
    for folder in list_folder:
      list_inModel_folder = np.array(os.listdir(os.path.join(drive_path, folder)))
      list_inModel_folder.sort()
      weights_path = os.path.join(drive_path, 'weights')
      model_weights = f"{folder}.pth"
      for file in list_inModel_folder:
        if file.startswith('added_') and os.path.exists(os.path.join(weights_path, model_weights)):
          array_final_folders.append(folder)
      time.sleep(0.1)
      progress_text = f'Scanning... {pbar.n}/{pbar.total}'
      percent = (pbar.n / pbar.total)
      display_progress(progress_text, percent, progress)
      pbar.update(1)
    Message = f"Scan complete. There is {len(array_final_folders)} models available"
    return(Message, [model for model in array_final_folders])

def get_available_model(model):
  message, model = scan_model()
  global model_value
  model_value = model
  return(message, gr.Dropdown(choices=model))

def copy_model(selected_model, progress=gr.Progress()):
  with tqdm(total=len(selected_model), desc="Copying model...", unit='Model') as pbar:
    for model in selected_model:
      progress_text = f'Copying model ({model})...'
      percent = pbar.n/pbar.total
      display_progress(progress_text, percent, progress)
      pbar.set_description(progress_text)
      
      #preparation
      rvc_model_path = os.path.join(rvc_models_dir, model)
      if not os.path.exists(rvc_model_path):
        rvc_model_path = os.makedirs(rvc_model_path)
        rvc_model_path = os.path.join(rvc_models_dir, model)
      model_dir_drive = os.path.join(drive_path, model)
      weight_dir = os.path.join(drive_path, 'weights')

      #copy model section
      in_model_list_folder_drive = os.listdir(model_dir_drive)
      #index file copy
      for file in in_model_list_folder_drive:
        if file.startswith('added') and file.endswith('.index'):
          index_path = os.path.join(model_dir_drive, file)
          dest_path = os.path.join(rvc_model_path, file)
          sh.copy(index_path, dest_path)
      #weight file copy
      in_weights_list = os.listdir(weight_dir)
      for file in in_weights_list:
        if file.startswith(f'{model}') and file.endswith('.pth'):
          model_weights_path = os.path.join(weight_dir, file)
          dest_path = os.path.join(rvc_model_path, file)
          sh.copy(model_weights_path, dest_path)
      pbar.update(1)
  return 'Models has been successfully copied'

def deselect(model_list, checkbox):
  return(gr.Dropdown(value=[]), gr.Checkbox(value=False))

def select_all_models(model_list, select_all):
  if select_all == True:
    return gr.Dropdown(value=model_value)
  else:
    return gr.Dropdown(value=[])

def copy_model_tab():
    #Scanning model section       
    with gr.Accordion('Scan models on /content/drive/MyDrive/RVC', open=True):
      with gr.Row():
        scan_model_button = gr.Button(value='Scan model 🔍', variant="primary")
        output1 = gr.Text(label='Output', interactive=False)
        
    #Models copy section
    with gr.Accordion('Choose model you want to copy into model_dir'):
      with gr.Row():
        with gr.Column(scale=1):
          model_list = gr.Dropdown(multiselect=True, label='Available Models List', info='There is all models that succesfuly scanned. You can chose one or more and click copy button to copy in rvc/model_dir', scale=1, allow_custom_value=True)
        with gr.Column(scale=0):
          select_all = gr.Checkbox(value=False, label='Select All')
          with gr.Row():
            deselect_button = gr.Button(value='Deselect', scale=1, min_width=100) 
            copy_model_button = gr.Button(value="Copy model", variant='primary',scale=1, min_width=100)
        with gr.Column(scale=0):
          output2 = gr.Textbox(label='Output',)
                  

    #Action section
    scan_model_button.click(get_available_model, inputs=[model_list], outputs=[output1, model_list])
    copy_model_button.click(copy_model, inputs=[model_list], outputs=output2)
    select_all.change(select_all_models, inputs=[model_list, select_all], outputs=[model_list])
    deselect_button.click(deselect, inputs=[model_list, select_all], outputs=[model_list, select_all])