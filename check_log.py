import os


def check_access_log():
    log_exists = True
    data_info = dict()
    data = list()

    if not os.path.exists(access_log):
        log_exists = False

    else:
        with open(access_log, "r") as f:

            while True:
                line = f.readline()
                if not line:
                    break

                line_tmp = line.strip("\n").split(" ")
                ip_addr = line_tmp[-1]
                access_times = line_tmp[-2]
                data.append([ip_addr, access_times])

    data_info["logfile_exists"] = log_exists
    data_info["data"] = data

    return data_info


if __name__ == "__main__":
    access_log = "logfiles/nginx_access.log"
    data_info = check_access_log()
    print(data_info)






