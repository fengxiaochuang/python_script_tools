import datetime
import os
import shutil
import zipfile
from urllib.parse import urlparse, ParseResult

import paramiko
from paramiko import SFTPClient


def get_remote_sftp_client(connection_params):
    res: ParseResult = urlparse(connection_params)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    hostname = res.hostname
    port = res.port
    username = res.username
    password = res.password
    client.connect(hostname=hostname, port=port, username=username, password=password)
    sftp_client: SFTPClient = client.open_sftp()
    return sftp_client


def get_remote_file_list(connection_params: str):
    """
    获取远程文件路径
    :param connection_params:
    :return:
    """
    res: ParseResult = urlparse(connection_params)
    sftp_client = get_remote_sftp_client(connection_params)
    paths = sftp_client.listdir(res.path)
    sftp_client.close()
    return paths


def get_remote_file(connection_params: str, local_path: str):
    """
    远程文件copy到本地
    :param connection_params:
    :param local_path:
    :return:
    """
    res: ParseResult = urlparse(connection_params)
    sftp_client = get_remote_sftp_client(connection_params)
    sftp_client.get(res.path, local_path)


def judge_mode(path, file=None):
    abs_file = path
    if file is not None:
        abs_file = os.path.join(path, file)
    if not os.access(abs_file, os.W_OK):
        os.chmod(abs_file, os.stat.S_IWOTH)


def remove_dir(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for file in files:
            judge_mode(root, file)
            os.remove(os.path.join(root, file))
        for doc in dirs:
            judge_mode(root, doc)
            os.rmdir(os.path.join(root, doc))


def get_remote_files(connection_params: str, remote_files: list, local_dir: str):
    """
    远程文件copy到本地
    :param connection_params: 连接串
    :param remote_files:  远端文件列表, 不带路径前缀
    :param local_dir:  本地路径
    :return:
    """
    res: ParseResult = urlparse(connection_params)
    sftp_client = get_remote_sftp_client(connection_params)
    remote_files = list(remote_files)
    for i in range(len(remote_files)):
        filename = remote_files[i]
        local_path = os.path.join(local_dir, filename)
        remove_path = os.path.join(res.path, filename).replace("\\", "/")
        sftp_client.get(remove_path, local_path)
        sftp_client.close()
    sftp_client.close()


def get_file_list(path: str):
    """
    获取排序后的文件路径
    :param path:
    :return:
    """
    if path.startswith("sftp"):
        path_list = get_remote_file_list(path)
    else:
        path_list = os.listdir(path)

    return sorted(path_list)


def zip_files(path, file_list):
    """
    自动收集列表文件，并打包成zip包
    :param path:
    :param file_list:
    :return:
    """
    datetime_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), datetime_str))
    if len(file_list) > 0:
        os.mkdir(local_dir)
        if path.startswith("sftp"):
            get_remote_files(path, file_list, local_dir)
        else:
            for file_item in file_list:
                shutil.copy(os.path.join(path, file_item), os.path.join(local_dir, file_item))

        # 压缩文件
        zip_file_name = local_dir + ".zip"
        with zipfile.ZipFile(zip_file_name, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(local_dir):
                zf.write(os.path.join(local_dir, filename), arcname=filename)
        os.chdir(os.path.dirname(__file__))
        print("压缩文件已自动生成: " + zip_file_name)
        remove_dir(local_dir)


if __name__ == '__main__':
    local_lib_path = r"E:\project\java\lib"
    server_68_lib_path = "sftp://user:password@10.0.1.10:22/server/path/"
    server_57_lib_path = "sftp://user:password@10.0.1.20:22/server/path/"

    source_path = local_lib_path
    target_path = server_57_lib_path

    source_path_list = get_file_list(source_path)
    target_path_list = get_file_list(target_path)

    # 新增包
    new_files = set(source_path_list) - set(target_path_list)
    if len(new_files) > 0:
        print("！！！新增文件: \n\t" + "\n\t".join(sorted(new_files)))
    else:
        print("无新增文件")
    # 减少包
    remove_files = set(target_path_list) - set(source_path_list)
    if len(remove_files) > 0:
        print("！！！移除文件: \n\t" + "\n\t".join(sorted(remove_files)))
        print("-------------------------------------")
        res: ParseResult = urlparse(target_path)
        for file in remove_files:
            print("rm -rf " + os.path.join(res.path, file).replace("\\", "/"))
        print("-------------------------------------")
    else:
        print("无移除文件")

    # 差异文件自动收集 自动打包
    zip_files(source_path, new_files)
