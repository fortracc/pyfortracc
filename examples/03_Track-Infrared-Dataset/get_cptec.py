import os
import pandas as pd
import pathlib
import urllib.request
import requests
import regex as re
import time
import argparse


def get_latest_file(timestamp, nprev = -1):
    response = requests.get(url + channel + timestamp.strftime('/%Y/%m/'))
    if response.status_code == 200:
        response_str = response.text
        files = re.findall(r'href=[\'"]?([^\'" >]+)', response_str)
        files = [file for file in files if file.endswith('.nc')]
        latest_file = list(dict.fromkeys(files))[nprev:]
        if len(latest_file) > 1:
            return latest_file
        return latest_file[0]
    else:
        None

def download_file(file):
    file = url + channel + timestamp.strftime('/%Y/%m/') + file
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
    for i in range(3):
        try:
            print('Downloading file: {}'.format(file))
            urllib.request.urlretrieve(file, output_path + file.split('/')[-1])
        except:
            print('Error downloading file: {}'.format(file))
            time.sleep(5)
            continue
        return

if __name__ == '__main__':

    url = 'http://ftp.cptec.inpe.br/goes/goes16/retangular/'

    parser = argparse.ArgumentParser(description='Download GOES-16 data from FTP server.')
    parser.add_argument('--n', type=int, default=3, help='Number of previous files to download')
    parser.add_argument('--c', type=str, default='ch13', help='Channel to download')
    parser.add_argument('--p', type=str, default='input/', help='Output path to save files')
    args = parser.parse_args()
    # Argumentos
    n_prev = args.n
    channel = args.c
    output_path = args.p

    # Create output directory
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)

    # Remove all files into output_path
    for file in os.listdir(output_path):
        os.remove(output_path + file)

    timestamp = pd.Timestamp.now()
    latest_files = get_latest_file(timestamp, nprev=-n_prev)
    for file in latest_files:
        download_file(file)

    # Wait for new files
    # last_file = None
    # while True:
    #     timestamp = pd.Timestamp.now()
    #     latest_file = get_latest_file(timestamp)
    #     if latest_file is not None and latest_file != last_file:
    #         download_file(latest_file)
    #     else:
    #         wtime = 300
    #         print('No new file found at {} wait for {} seconds'.format(timestamp, wtime))
    #         time.sleep(wtime)
    #     last_file = latest_file

