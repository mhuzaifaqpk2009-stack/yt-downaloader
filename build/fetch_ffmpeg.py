import urllib.request, zipfile, os, shutil 
url = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' 
urllib.request.urlretrieve(url, 'ffmpeg.zip') 
with zipfile.ZipFile('ffmpeg.zip') as z: 
    for f in z.namelist(): 
        if f.endswith('bin/ffmpeg.exe'): 
            with z.open(f) as src, open('ffmpeg.exe', 'wb') as dst: shutil.copyfileobj(src, dst) 
            break 
os.remove('ffmpeg.zip') 
