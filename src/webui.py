import json
import os
import shutil
import urllib.request
import zipfile
from argparse import ArgumentParser

import gradio as gr

from main import song_cover_pipeline
from copy_model_from_drive import copy_model_tab
from footer import footer
import logging

logging.getLogger("numba").setLevel(logging.WARNING)

logging.getLogger("pydub.converter").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("matplotlib.pyplot").setLevel(logging.WARNING)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

mdxnet_models_dir = os.path.join(BASE_DIR, 'mdxnet_models')
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')
output_dir = os.path.join(BASE_DIR, 'song_output')


def get_current_models(models_dir):
    models_list = os.listdir(models_dir)
    items_to_remove = ['hubert_base.pt', 'MODELS.txt', 'public_models.json', 'rmvpe.pt']
    return [item for item in models_list if item not in items_to_remove]


def update_models_list():
    models_l = get_current_models(rvc_models_dir)
    return gr.Dropdown(choices=sorted(models_l)), gr.Dropdown(choices=sorted(models_l))


def load_public_models():
    models_table = []
    for model in public_models['voice_models']:
        if not model['name'] in voice_models:
            model = [model['name'], model['description'], model['credit'], model['url'], ', '.join(model['tags'])]
            models_table.append(model)

    tags = list(public_models['tags'].keys())
    return gr.DataFrame.update(value=models_table), gr.CheckboxGroup.update(choices=tags)


def extract_zip(extraction_folder, zip_name):
    os.makedirs(extraction_folder)
    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        zip_ref.extractall(extraction_folder)
    os.remove(zip_name)

    index_filepath, model_filepath = None, None
    for root, dirs, files in os.walk(extraction_folder):
        for name in files:
            if name.endswith('.index') and os.stat(os.path.join(root, name)).st_size > 1024 * 100:
                index_filepath = os.path.join(root, name)

            if name.endswith('.pth') and os.stat(os.path.join(root, name)).st_size > 1024 * 1024 * 40:
                model_filepath = os.path.join(root, name)

    if not model_filepath:
        raise gr.Error(f'No .pth model file was found in the extracted zip. Please check {extraction_folder}.')

    # move model and index file to extraction folder
    os.rename(model_filepath, os.path.join(extraction_folder, os.path.basename(model_filepath)))
    if index_filepath:
        os.rename(index_filepath, os.path.join(extraction_folder, os.path.basename(index_filepath)))

    # remove any unnecessary nested folders
    for filepath in os.listdir(extraction_folder):
        if os.path.isdir(os.path.join(extraction_folder, filepath)):
            shutil.rmtree(os.path.join(extraction_folder, filepath))


def download_online_model(url, dir_name, progress=gr.Progress()):
    try:
        progress(0, desc=f'[~] Downloading voice model with name {dir_name}...')
        zip_name = url.split('/')[-1]
        extraction_folder = os.path.join(rvc_models_dir, dir_name)
        if os.path.exists(extraction_folder):
            raise gr.Error(f'Voice model directory {dir_name} already exists! Choose a different name for your voice model.')

        if 'pixeldrain.com' in url:
            url = f'https://pixeldrain.com/api/file/{zip_name}'

        urllib.request.urlretrieve(url, zip_name)

        progress(0.5, desc='[~] Extracting zip...')
        extract_zip(extraction_folder, zip_name)
        return f'[+] {dir_name} Model successfully downloaded!'

    except Exception as e:
        raise gr.Error(str(e))


def upload_local_model(zip_path, dir_name, progress=gr.Progress()):
    try:
        extraction_folder = os.path.join(rvc_models_dir, dir_name)
        if os.path.exists(extraction_folder):
            raise gr.Error(f'Voice model directory {dir_name} already exists! Choose a different name for your voice model.')

        zip_name = zip_path.name
        progress(0.5, desc='[~] Extracting zip...')
        extract_zip(extraction_folder, zip_name)
        return f'[+] {dir_name} Model successfully uploaded!'

    except Exception as e:
        raise gr.Error(str(e))


def filter_models(tags, query):
    models_table = []

    # no filter
    if len(tags) == 0 and len(query) == 0:
        for model in public_models['voice_models']:
            models_table.append([model['name'], model['description'], model['credit'], model['url'], model['tags']])

    # filter based on tags and query
    elif len(tags) > 0 and len(query) > 0:
        for model in public_models['voice_models']:
            if all(tag in model['tags'] for tag in tags):
                model_attributes = f"{model['name']} {model['description']} {model['credit']} {' '.join(model['tags'])}".lower()
                if query.lower() in model_attributes:
                    models_table.append([model['name'], model['description'], model['credit'], model['url'], model['tags']])

    # filter based on only tags
    elif len(tags) > 0:
        for model in public_models['voice_models']:
            if all(tag in model['tags'] for tag in tags):
                models_table.append([model['name'], model['description'], model['credit'], model['url'], model['tags']])

    # filter based on only query
    else:
        for model in public_models['voice_models']:
            model_attributes = f"{model['name']} {model['description']} {model['credit']} {' '.join(model['tags'])}".lower()
            if query.lower() in model_attributes:
                models_table.append([model['name'], model['description'], model['credit'], model['url'], model['tags']])

    return gr.DataFrame(value=models_table)


def pub_dl_autofill(pub_models, event: gr.SelectData):
    return gr.Text.update(value=pub_models.loc[event.index[0], 'URL']), gr.Text.update(value=pub_models.loc[event.index[0], 'Model Name'])


def swap_visibility():
    return gr.update(visible=True), gr.update(visible=False), gr.update(value=''), gr.update(value=None)


def process_file_upload(file):
    return file.name, gr.update(value=file.name)


def show_hop_slider(pitch_detection_algo):
    if pitch_detection_algo == 'mangio-crepe':
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)
    
def show_backvoc_slider(use_backvoc):
    if use_backvoc == True:
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)
    
def separate_method(sep_method):
    # Kode untuk "skip queue" atau melompati antrian
    pass

def back_voice_models(value):
    # Kode untuk "skip loading" atau melompati antrian
    return value


def show_backvocPitch_slider(backvoc_infer):
    if backvoc_infer == True:
        return gr.update(visible=True), gr.update(visible=True)
    else:
        return gr.update(visible=False), gr.update(visible=False, value='')

if __name__ == '__main__':
    parser = ArgumentParser(description='Generate a AI cover song in the song_output/id directory.', add_help=True)
    parser.add_argument("--share", action="store_true", dest="share_enabled", default=False, help="Enable sharing")
    parser.add_argument("--listen", action="store_true", default=False, help="Make the WebUI reachable from your local network.")
    parser.add_argument('--listen-host', type=str, help='The hostname that the server will use.')
    parser.add_argument('--listen-port', type=int, help='The listening port that the server will use.')
    args = parser.parse_args()

    voice_models = get_current_models(rvc_models_dir)

    with open(os.path.join(rvc_models_dir, 'public_models.json'), encoding='utf8') as infile:
        public_models = json.load(infile)

    with gr.Blocks(title='AICoverGenWebUI', theme='NoCrypt/miku', ) as app:

        gr.Label('AICoverGen WebUI created with ❤️ (modded)', show_label=False)

        # main tab
        with gr.Tab("Generate"):

            with gr.Accordion('Main Options'):
                with gr.Row():
                    with gr.Column():
                        rvc_model = gr.Dropdown(sorted(voice_models), label='Voice Models', info='Models folder "AICoverGen --> rvc_models". After new models are added into this folder, click the refresh button')
                        rvc_backup_model = gr.Dropdown(sorted(voice_models), label='Backup Voice Models', visible=False)
                        rvc_backup_model.change(back_voice_models, inputs=rvc_backup_model, outputs=rvc_backup_model)
                        ref_btn = gr.Button('Refresh Models 🔁', variant='primary')

                    with gr.Column() as yt_link_col:
                        song_input = gr.Text(label='Song input', info='Link to a song on YouTube or full path to a local file. For file upload, click the button below.')
                        show_file_upload_button = gr.Button('Upload file instead')

                    with gr.Column(visible=False) as file_upload_col:
                        local_file = gr.File(label='Audio file')
                        song_input_file = gr.UploadButton('Upload 📂', file_types=['audio'], variant='primary')
                        show_yt_link_button = gr.Button('Paste YouTube link/Path to local file instead')
                        song_input_file.upload(process_file_upload, inputs=[song_input_file], outputs=[local_file, song_input])

                    with gr.Column():
                        pitch = gr.Slider(-24, 24, value=0, step=1, label='Pitch Change (Vocals ONLY)', info='Generally, use 12 for male to female conversions and -12 for vice-versa. (Octaves)')
                        back_vocal_pitch = gr.Slider(-24, 24, value=0, step=1, label='Pitch Change (Back Vocals ONLY)', info='Generally, use 12 for male to female conversions and -12 for vice-versa. (Octaves)', visible=False)
                        pitch_all = gr.Slider(-12, 12, value=0, step=1, label='Overall Pitch Change', info='Changes pitch/key of vocals and instrumentals together. Altering this slightly reduces sound quality. (Semitones)')
                    show_file_upload_button.click(swap_visibility, outputs=[file_upload_col, yt_link_col, song_input, local_file])
                    show_yt_link_button.click(swap_visibility, outputs=[yt_link_col, file_upload_col, song_input, local_file])

            with gr.Accordion('Voice conversion options', open=False):
                with gr.Row():
                    index_rate = gr.Slider(0, 1, value=0.6, label='Index Rate', info="Controls how much of the AI voice's accent to keep in the vocals")
                    filter_radius = gr.Slider(0, 7, value=3, step=1, label='Filter radius', info='If >=3: apply median filtering median filtering to the harvested pitch results. Can reduce breathiness')
                    rms_mix_rate = gr.Slider(0, 1, value=0.25, label='RMS mix rate', info="Control how much to mimic the original vocal's loudness (0) or a fixed loudness (1)")
                    protect = gr.Slider(0, 0.5, value=0.33, label='Protect rate', info='Protect voiceless consonants and breath sounds. Set to 0.5 to disable.')
                    with gr.Column():
                        f0_method = gr.Dropdown(['rmvpe', 'mangio-crepe'], value='rmvpe', label='Pitch detection algorithm', info='Best option is rmvpe (clarity in vocals), then mangio-crepe (smoother vocals)')
                        crepe_hop_length = gr.Slider(32, 320, value=128, step=1, visible=False, label='Crepe hop length', info='Lower values leads to longer conversions and higher risk of voice cracks, but better pitch accuracy.')
                        f0_method.change(show_hop_slider, inputs=f0_method, outputs=crepe_hop_length)
                keep_files = gr.Checkbox(label='Keep intermediate files', info='Keep all audio files generated in the song_output/id directory, e.g. Isolated Vocals/Instrumentals. Leave unchecked to save space')
                backvoc_infer = gr.Checkbox(label='Use RVC into backvocal', info='Do RVC Conversion into backvocal')
                backvoc_infer.change(show_backvocPitch_slider, inputs=backvoc_infer, outputs=[back_vocal_pitch, rvc_backup_model])

            with gr.Accordion('Vocal separation options', open=False):
                sep_method = gr.Dropdown(['UVR-MDXNET', 'Demucs'], value='', label='Vocal separate algorithm', info='UVR-MDXNET (better vocal separate), Demucs (better for instrument) __NEW FEATURES__')
                sep_method.change(separate_method)#, inputs=[sep_method], outputs=[sep_method])
    
            with gr.Accordion('Audio mixing options', open=False):
                using_backvoc = gr.Checkbox(label='Separate back vocal too', info='Separate back vocal to better output (checklist to separate back vocal)', value=True)
                gr.Markdown('### Volume Change (decibels)')
                with gr.Row():
                    main_gain = gr.Slider(-20, 20, value=0, step=1, label='Main Vocals')
                    backup_gain = gr.Slider(-20, 20, value=0, step=1, label='Backup Vocals')
                    inst_gain = gr.Slider(-20, 20, value=0, step=1, label='Music', visible='true')

                    using_backvoc.change(show_backvoc_slider, inputs=using_backvoc, outputs=backup_gain)

                gr.Markdown('### Reverb Control on AI Vocals')
                with gr.Row():
                    reverb_rm_size = gr.Slider(0, 1, value=0.15, label='Room size', info='The larger the room, the longer the reverb time')
                    reverb_wet = gr.Slider(0, 1, value=0.2, label='Wetness level', info='Level of AI vocals with reverb')
                    reverb_dry = gr.Slider(0, 1, value=0.8, label='Dryness level', info='Level of AI vocals without reverb')
                    reverb_damping = gr.Slider(0, 1, value=0.7, label='Damping level', info='Absorption of high frequencies in the reverb')

                gr.Markdown('### Audio Output Format')
                output_format = gr.Dropdown(['mp3', 'wav'], value='mp3', label='Output file type', info='mp3: small file size, decent quality. wav: Large file size, best quality')

            with gr.Row():
                clear_btn = gr.ClearButton(value='Clear', components=[song_input, rvc_model, keep_files, local_file])
                generate_btn = gr.Button("Generate", variant='primary')
                ai_cover = gr.Audio(label='AI Cover', show_share_button=False)

            ref_btn.click(update_models_list, None, outputs=[rvc_model, rvc_backup_model])
            is_webui = gr.Number(value=1, visible=False)
            generate_btn.click(song_cover_pipeline,
                               inputs=[song_input, rvc_model, rvc_backup_model, pitch, keep_files, is_webui, main_gain, backup_gain,
                                       inst_gain, index_rate, filter_radius, rms_mix_rate, f0_method, crepe_hop_length,
                                       protect, pitch_all, reverb_rm_size, reverb_wet, reverb_dry, reverb_damping,
                                       output_format, using_backvoc, sep_method, backvoc_infer, back_vocal_pitch],
                               outputs=[ai_cover])
            clear_btn.click(lambda: [0, 0, 0, 0, 0.6, 3, 0.25, 0.33, 'rmvpe', 128, 0, 0.15, 0.2, 0.8, 0.7, 'mp3', None, True, 'UVR-MDXNET'],
                            outputs=[pitch, main_gain, backup_gain, inst_gain, index_rate, filter_radius, rms_mix_rate,
                                     protect, f0_method, crepe_hop_length, pitch_all, reverb_rm_size, reverb_wet,
                                     reverb_dry, reverb_damping, output_format, ai_cover, using_backvoc])

        # Download tab
        with gr.Tab('Download model'):

            with gr.Tab('From HuggingFace/Pixeldrain URL'):
                with gr.Row():
                    model_zip_link = gr.Text(label='Download link to model', info='Should be a zip file containing a .pth model file and an optional .index file.')
                    model_name = gr.Text(label='Name your model', info='Give your new model a unique name from your other voice models.')

                with gr.Row():
                    download_btn = gr.Button('Download 🌐', variant='primary', scale=19)
                    dl_output_message = gr.Text(label='Output Message', interactive=False, scale=20)

                download_btn.click(download_online_model, inputs=[model_zip_link, model_name], outputs=dl_output_message)

                gr.Markdown('## Input Examples')
                gr.Examples(
                    [
                        ['https://huggingface.co/phant0m4r/LiSA/resolve/main/LiSA.zip', 'Lisa'],
                        ['https://pixeldrain.com/u/3tJmABXA', 'Gura'],
                        ['https://huggingface.co/Kit-Lemonfoot/kitlemonfoot_rvc_models/resolve/main/AZKi%20(Hybrid).zip', 'Azki']
                    ],
                    [model_zip_link, model_name],
                    [],
                    download_online_model,
                )

            with gr.Tab('From Public Index'):

                gr.Markdown('## How to use')
                gr.Markdown('- Click Initialize public models table')
                gr.Markdown('- Filter models using tags or search bar')
                gr.Markdown('- Select a row to autofill the download link and model name')
                gr.Markdown('- Click Download')

                with gr.Row():
                    pub_zip_link = gr.Text(label='Download link to model')
                    pub_model_name = gr.Text(label='Model name')

                with gr.Row():
                    download_pub_btn = gr.Button('Download 🌐', variant='primary', scale=19)
                    pub_dl_output_message = gr.Text(label='Output Message', interactive=False, scale=20)

                filter_tags = gr.CheckboxGroup(value=[], label='Show voice models with tags', choices=[])
                search_query = gr.Text(label='Search')
                load_public_models_button = gr.Button(value='Initialize public models table', variant='primary')

                public_models_table = gr.DataFrame(value=[], headers=['Model Name', 'Description', 'Credit', 'URL', 'Tags'], label='Available Public Models', interactive=False)
                public_models_table.select(pub_dl_autofill, inputs=[public_models_table], outputs=[pub_zip_link, pub_model_name])
                load_public_models_button.click(load_public_models, outputs=[public_models_table, filter_tags])
                search_query.change(filter_models, inputs=[filter_tags, search_query], outputs=public_models_table)
                filter_tags.change(filter_models, inputs=[filter_tags, search_query], outputs=public_models_table)
                download_pub_btn.click(download_online_model, inputs=[pub_zip_link, pub_model_name], outputs=pub_dl_output_message)

        # Upload tab
        with gr.Tab('Upload model'):
            gr.Markdown('## Upload locally trained RVC v2 model and index file')
            gr.Markdown('- Find model file (weights folder) and optional index file (logs/[name] folder)')
            gr.Markdown('- Compress files into zip file')
            gr.Markdown('- Upload zip file and give unique name for voice')
            gr.Markdown('- Click Upload model')

            with gr.Row():
                with gr.Column():
                    zip_file = gr.File(label='Zip file')

                local_model_name = gr.Text(label='Model name')

            with gr.Row():
                model_upload_button = gr.Button('Upload model', variant='primary', scale=19)
                local_upload_output_message = gr.Text(label='Output Message', interactive=False, scale=20)
                model_upload_button.click(upload_local_model, inputs=[zip_file, local_model_name], outputs=local_upload_output_message)
        # Copy model from drive tab
        with gr.Tab('Copy model from drive'):
          copy_model_tab()

        gr.HTML(footer)
    
    app.queue()

    print("\n--------------------------------------------\n")
    
    app.launch(
        share=args.share_enabled,
        server_name=None if not args.listen else (args.listen_host or '0.0.0.0'),
        server_port=args.listen_port,
    )
