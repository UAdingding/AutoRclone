# auto rclone
#
# Author Telegram https://t.me/CodyDoby
# Inbox  codyd@qq.com
#
# can copy from
# - [x] publicly shared folder to Team Drive
# - [x] Team Drive to Team Drive
# - [x] publicly shared folder to publicly shared folder (with write privilege)
# - [x] Team Drive to publicly shared folder
#   `python3 .\rclone_sa_magic.py -s SourceID -d DestinationID -dp DestinationPathName -b 10`
#
# - [x] local to Team Drive
# - [ ] local to private folder
# - [ ] private folder to any (think service accounts cannot do anything about private folder)
#
import argparse
import glob
import json
import os
import platform
import subprocess
import sys
import time
from signal import signal, SIGINT

# =================modify here=================
logfile = "log_rclone.txt"  # log file: tail -f log_rclone.txt
NAME_SCREEN = "wrc"         # default value. Will be replaced by parameters input (-n)

# parameters for this script
SIZE_GB_MAX = 735          # if one account has already copied 735GB, switch to next account
CNT_403_RETRY = 100        # if there is no files be copied for 100 times, switch to next account
CNT_SA_EXIT = 3           # if continually switch account for 3 times stop script

# change it when u know what are u doing
# paramters for rclone.
# If TPSLIMITxTRANSFERS is too big, will cause 404 user rate limit error,
# especially for tasks with a lot of small files
TPSLIMIT = 3
TRANSFERS = 3
# =================modify here=================


def is_windows():
    return platform.system() == 'Windows'


def handler(signal_received, frame):
    global NAME_SCREEN

    if is_windows():
        kill_cmd = 'taskkill /IM "rclone.exe" /F'
    else:
        kill_cmd = "screen -r -S %s -X quit" % NAME_SCREEN

    try:
        print("\n" + " "*20 + " {}".format(time.strftime("%H:%M:%S")))
        subprocess.check_call(kill_cmd, shell=True)
    except:
        pass
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(description="Copy from source (publicly local/shared drive/Team Drive/) "
                                                 "to destination (publicly shared drive/Team Drive).")
    parser.add_argument('-s', '--source_id', type=str,
                        help='the id of source. Team Drive id or publicly shared folder id')
    parser.add_argument('-d', '--destination_id', type=str, required=True,
                        help='the id of destination. Team Drive id or publicly shared folder id')

    parser.add_argument('-sp', '--source_path', type=str, default="",
                        help='the folder path of source. In Google Drive or local.')
    parser.add_argument('-dp', '--destination_path', type=str, default="",
                        help='the folder path of destination. In Google Drive.')

    parser.add_argument('-sa', '--service_account', type=str, default="accounts",
                        help='the folder path of json files for service accounts.')

    parser.add_argument('-n', '--name_screen', type=str, default="wrc",
                        help='the name of screen. Set it to different if you want to run more than one instance.')

    parser.add_argument('-b', '--begin_sa_id', type=int, default=1,
                        help='the begin id of sa for source')
    parser.add_argument('-e', '--end_sa_id', type=int, default=400,
                        help='the end id of sa for destination')

    parser.add_argument('-c', '--rclone_config_file', type=str,
                        help='config file path of rclone')
    parser.add_argument('-t', '--test_only', action="store_true",
                        help='for test: make rclone dry-run')

    parser.add_argument('--disable_list_r', action="store_true",
                        help='for debug. do not use this.')

    args = parser.parse_args()
    return args


def gen_rclone_cfg(args):
    sa_files = glob.glob(os.path.join(args.service_account, '*.json'))
    output_of_config_file = './rclone.conf'

    if len(sa_files)==0:
        sys.exit('No json files found in {}'.format(args.service_account))

    with open(output_of_config_file, 'w') as fp:
        for i, filename in enumerate(sa_files):

            dir_path = os.path.dirname(os.path.realpath(__file__))
            filename = os.path.join(dir_path, filename)
            filename = filename.replace(os.sep, '/')

            # For source
            if args.source_id:
                if len(args.source_id) == 33:
                    folder_or_team_drive_src = 'root_folder_id'
                elif len(args.source_id) == 19:
                    folder_or_team_drive_src = 'team_drive'
                else:
                    return print('Wrong length of team_drive_id or publicly shared root_folder_id')

                try:
                    fp.write('[{}{:03d}]\n'
                             'type = drive\n'
                             'scope = drive\n'
                             'service_account_file = {}\n'
                             '{} = {}\n\n'.format('src', i + 1, filename, folder_or_team_drive_src, args.source_id))
                except:
                    return print("failed to write {} to {}".format(args.source_id, output_of_config_file))
            else:
                pass

            # For destination
            if len(args.destination_id) == 33:
                folder_or_team_drive_dst = 'root_folder_id'
            elif len(args.destination_id) == 19:
                folder_or_team_drive_dst = 'team_drive'
            else:
                return print('Wrong length of team_drive_id or publicly shared root_folder_id')

            try:
                fp.write('[{}{:03d}]\n'
                         'type = drive\n'
                         'scope = drive\n'
                         'service_account_file = {}\n'
                         '{} = {}\n\n'.format('dst', i, filename, folder_or_team_drive_dst, args.destination_id))
            except:
                return print("failed to write {} to {}".format(args.destination_id, output_of_config_file))

    return output_of_config_file, i


def print_during(time_start):
    time_stop = time.time()
    hours, rem = divmod((time_stop - time_start), 3600)
    minutes, sec = divmod(rem, 60)
    print("Elapsed Time: {:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), sec))


def main():
    signal(SIGINT, handler)

    args = parse_args()

    global NAME_SCREEN
    NAME_SCREEN = args.name_screen

    id = args.begin_sa_id
    end_id = args.end_sa_id

    config_file = args.rclone_config_file
    if config_file is None:
        print('generating rclone config file.')
        config_file, end_id = gen_rclone_cfg(args)
        print('rclone config file generated.')
    else:
        return print('not supported yet.')
        pass
        # need parse labels from config files

    time_start = time.time()
    print("Start: " + str(time_start))

    while id <= end_id + 1:

        if id == end_id + 1:
            break
            # id = 1

        with open('current_sa.txt', 'w') as fp:
            fp.write(str(id) + '\n')

        src_label = "src" + "{0:03d}".format(id) + ":"
        dst_label = "dst" + "{0:03d}".format(id) + ":"

        src_full_path = src_label + args.source_path
        if args.source_id is None:
            src_full_path = args.source_path

        dst_full_path = dst_label + args.destination_path
        if args.destination_id is None:
            src_full_path = args.destination_path

        # =================cmd to run=================
        open_cmd = "rclone --config {} copy ".format(config_file)
        if args.test_only:
            open_cmd += "--dry-run "
        # --fast-list is default adopted in latest rclone
        open_cmd += "--drive-server-side-across-configs --rc -vv --ignore-existing "
        open_cmd += "--tpslimit {} --transfers {} --drive-chunk-size 32M ".format(TPSLIMIT, TRANSFERS)
        if args.disable_list_r:
            open_cmd += "--disable ListR "
        open_cmd += "--drive-acknowledge-abuse --log-file={} {} {}".format(logfile, src_full_path, dst_full_path)

        if not is_windows():
            open_cmd = "screen -d -m -S {} ".format(NAME_SCREEN) + open_cmd
        else:
            open_cmd = "start /b " + open_cmd
        # =================cmd to run=================

        print(open_cmd)

        try:
            subprocess.check_call(open_cmd, shell=True)
            print(">> Let us go {} {}".format(dst_label, time.strftime("%H:%M:%S")))
            time.sleep(10)
        except subprocess.SubprocessError as error:
            return print("error: " + str(error))

        cnt_error = 0
        cnt_403_retry = 0
        size_GB_done_before = 0
        cnt_exit = 0
        while True:
            cmd = 'rclone rc core/stats'
            try:
                response = subprocess.check_output(cmd, shell=True)
                cnt_error = 0
                cnt_exit = 0
            except subprocess.SubprocessError as error:
                # continually ...
                cnt_error = cnt_error + 1
                if cnt_error >= 5:
                    print('No rclone task detected (possibly done for this account).')
                    # Regard continually exit as *all done*.
                    if cnt_error >= 15:
                        return print('All done.')
                    break

                continue

            response_processed = response.decode('utf-8').replace('\0', '')
            response_processed_json = json.loads(response_processed)

            # print(response_processed_json)

            size_GB_done = int(int(response_processed_json['bytes']) * 9.31322e-10)
            speed_now = float(int(response_processed_json['speed']) * 9.31322e-10 * 1024)

            print("%s %dGB Done @ %fMB/s" % (dst_label, size_GB_done, speed_now), end="\r")

            # continually no ...
            if size_GB_done - size_GB_done_before == 0:
                cnt_403_retry += 1
            else:
                cnt_403_retry = 0

            size_GB_done_before = size_GB_done

            # Stop by error (403) info
            if size_GB_done >= SIZE_GB_MAX or cnt_403_retry >= CNT_403_RETRY:

                if is_windows():
                    kill_cmd = 'taskkill /IM "rclone.exe" /F'
                else:
                    kill_cmd = "screen -r -S %s -X quit" % NAME_SCREEN
                print("\n" + " "*20 + " {}".format(time.strftime("%H:%M:%S")))
                subprocess.check_call(kill_cmd, shell=True)
                print('\n')

                # =================Finish it=================
                if cnt_403_retry >= CNT_403_RETRY:
                    cnt_exit += 1
                else:
                    # clear cnt if there is one time
                    cnt_exit = 0

                # Regard continually exit as *all done*.
                if cnt_exit > CNT_SA_EXIT:
                    print_during(time_start)
                    # exit directly rather than switch to next account.
                    return print('All Done.')
                # =================Finish it=================

                break

            time.sleep(2)
        id = id + 1

    print_during(time_start)


if __name__ == "__main__":
    main()