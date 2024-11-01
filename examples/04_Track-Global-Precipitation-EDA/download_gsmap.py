import ftplib
import os
import argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Configurações de conexão
server = 'hokusai.eorc.jaxa.jp'
max_workers = 5  # Número de threads para download paralelo

def download_nc_files(ftp_details, current_dir, output_dir):
    server, user, passwd = ftp_details
    with ftplib.FTP(server) as ftp:
        ftp.login(user, passwd)
        try:
            ftp.cwd(current_dir)
            filenames = ftp.nlst()

            for filename in filenames:
                if is_nc_file(filename):
                    local_filename = os.path.join(output_dir, filename)
                    with open(local_filename, 'wb') as file:
                        ftp.retrbinary('RETR ' + filename, file.write)
                    print(f"Downloaded: {local_filename}")
        except ftplib.error_perm as e:
            print(f"Cannot access directory: {current_dir} - {e}")

def is_nc_file(filename):
    return filename.lower().endswith('.nc')

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def main(start_date_str, end_date_str, base_directory, user, passwd):
    output_dir = os.path.basename(os.path.normpath(base_directory))
    os.makedirs(output_dir, exist_ok=True)

    # Parse dates from arguments
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    ftp_details = (server, user, passwd)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for single_date in daterange(start_date, end_date):
            year = single_date.strftime('%Y')
            month = single_date.strftime('%m')
            day = single_date.strftime('%d')
            current_dir = os.path.join(base_directory, year, month, day)
            futures.append(executor.submit(download_nc_files, ftp_details, current_dir, output_dir))

        for future in futures:
            future.result()  # Espera a conclusão de todos os downloads

    print("Download completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download GSMaP data from FTP server.')
    parser.add_argument('start_date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('end_date', type=str, help='End date in YYYY-MM-DD format')
    parser.add_argument('base_directory', type=str, help='Base directory on FTP server (e.g., /realtime_ver/v8/netcdf/)')
    parser.add_argument('user', type=str, help='FTP username')
    parser.add_argument('passwd', type=str, help='FTP password')
    args = parser.parse_args()
    main(args.start_date, args.end_date, args.base_directory, args.user, args.passwd)
