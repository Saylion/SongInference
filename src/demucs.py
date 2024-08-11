import re
import os
import glob
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def rename(orig_song_path):
    filename = orig_song_path
    if orig_song_path.startswith('/'):
        split_orig_song_path = orig_song_path.split('/')
        if split_orig_song_path[-1]:
            file = split_orig_song_path[-1]
            file = re.sub(r'[^a-zA-Z0-9.]', '_', file)
            split_orig_song_path.pop()
            filename = '/'.join(split_orig_song_path) + '/' + file
            os.rename(orig_song_path, filename)
    else:
        filename = re.sub(r'[^a-zA-Z0-9.]', '_', orig_song_path)
        search_file_mp3 = glob.glob("*.mp3")
        for file in search_file_mp3:
          new_name = filename

          os.rename(file, new_name)

    return filename

def run_demucs(song_output_dir, orig_song_path, keep_orig):
    if orig_song_path.startswith('/') and not orig_song_path.startswith('/tmp/'):
      orig_song_path = shutil.copy(orig_song_path, BASE_DIR)

    filename = rename(orig_song_path)

    get_model = 'htdemucs'

    command = f'demucs --two-stems=vocals -n {get_model} --out {song_output_dir} {filename}'

    subprocess.run(command.split(), stdout=subprocess.PIPE)

    sep_path = os.path.join(song_output_dir,get_model,f"{os.path.basename(os.path.splitext(filename)[0])}")

    #Vocals path
    vocal_path = os.path.join(song_output_dir, f'{os.path.basename(os.path.splitext(orig_song_path)[0])}_Vocals.wav')
    
    if os.path.exists(vocal_path):
        os.remove(vocal_path)

    old_vocal_name = os.path.join(sep_path, 'vocals.wav')
    new_vocal_name = os.path.join(sep_path, f'{os.path.basename(os.path.splitext(orig_song_path)[0])}_Vocals.wav')
    os.rename(old_vocal_name, new_vocal_name)   
    shutil.move(new_vocal_name,song_output_dir)
    

    #Instrument path
    inst_path = os.path.join(song_output_dir, f'{os.path.basename(os.path.splitext(orig_song_path)[0])}_Instrumental.wav')

    if os.path.exists(inst_path):
        os.remove(inst_path)

    old_inst_name = os.path.join(sep_path, 'no_vocals.wav')
    new_inst_name = os.path.join(sep_path, f'{os.path.basename(os.path.splitext(orig_song_path)[0])}_Instrumental.wav')
    os.rename(old_inst_name, new_inst_name)
    shutil.move(new_inst_name,song_output_dir)
    if not orig_song_path.startswith('/tmp/'):
      os.remove(filename)
    else:
      os.rename(filename, orig_song_path)
    shutil.rmtree(f'{os.path.join(song_output_dir,get_model)}')

    return vocal_path, inst_path