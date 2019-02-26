#!/usr/bin/env python3  
# -*- coding: utf-8 -*-  
import os    
import os.path   
import paramiko  
import datetime  
import re  
import time
import shutil
import sys
import socket

# 配置属性  
config = {  
    #本地待同步文件夹路径  
    'local_path' : '/',
    
    # 服务器备份目标路径  
    'ssh_path' : '/',

    # 服务器端待同步文件夹路径
    'remote_path' : '/',
    
    #探测点定时每次睡眠时长（以秒为单位默认60s）
    'sleep seconds' : 6,
    
    #探测点每日向服务器同步的时刻 (24h制时间 格式为 HHMMSS ，默认120000）
    'SYNC trigger time' :  020000 ,
    
    #探测点每日删除本地数据的时刻 (24h制时间 格式为 HHMMSS ，默认220000)
    'delete trigger time': 220000 ,
    

    # ssh地址、端口、用户名、密码  
    'hostname' : '0.0.0.0',  
    'port' : 22,  
    'username' : '0000',
    'password' : '0000',
}  

#处理本地项目结尾的'/'
if config['local_path'][-1] == '/':
    config['local_path'] = config['local_path'][:-1]



def yesterday():
    date = str(datetime.date.today() - datetime.timedelta(days=1))
    flag = date.find("-")
    if date[flag+1]=='0':
        date = date[0:flag+1]+date[6:]
    date = date.replace("-","_")
    return date
  
def check_file(ssh,sftp,local_path, ssh_path):  
    '''
        检查文件是否存在，不存在直接上传 
        存在则进行校验，若大小不相同则重传
    ''' 
    stdin, stdout, stderr = ssh.exec_command('find ' + ssh_path)  
    result = stdout.read().decode('utf-8')  
    
    if len(result) == 0 :  
        print('%s 正在上传' % (ssh_path))  
        sftp.put(local_path,ssh_path)  
        print('%s 上传成功' % (ssh_path))  
        return 1  
    else:  
        #  存在则比较文件大小
        #  若文件大小不同则重新上传  
        #  本地文件大小  
        lf_size = os.path.getsize(local_path)  
        # 目标文件大小  
        stdin, stdout, stderr = ssh.exec_command('du -b ' + ssh_path)  
        result = stdout.read().decode('utf-8')  
        tf_size = int(result.split('\t')[0])  
        print('本地文件大小为：%s，远程文件大小为：%s' % (lf_size, tf_size))  
        if lf_size == tf_size:  
            print('%s 大小与本地文件相同，不更新' % (ssh_path))  
            return 0  
        else:  
            print('%s 正在更新' % (ssh_path))  
            sftp.put(local_path,ssh_path)  
            print('%s 更新成功' % (ssh_path))  
            return 1  

def check_remote_directory(ssh,ssh_file_list,yesterday_date):
    '''
        检查服务器端保存路径是否存在  
        不存在则创建目录
    '''
    root_path = config['ssh_path']+yesterday_date+'/' 
    stdin, stdout, stderr = ssh.exec_command('find ' + root_path)  
    result = stdout.read().decode('utf-8')  
    if len(result) == 0 :  
        print('目录 %s 不存在，创建目录' % root_path)  
        ssh.exec_command('mkdir -p ' + root_path)  
        print('%s 创建成功' % root_path)  
    else:  
        print('目录 %s 已存在' % root_path)  
        ssh_file_list = re.split('\n',result)   
    stdin, stdout, stderr = ssh.exec_command(' mv '+ config['remote_path']+yesterday_date+'/* '+ root_path) 
    stdin, stdout, stderr = ssh.exec_command(' rmdir '+ config['remote_path']+yesterday_date) 
    print (' mv '+ config['remote_path']+yesterday_date+'/* '+ root_path) 

def get_local_path(file_list,yesterday_date):
    '''
    获取待备份本地文件列表
    '''
    for pathstr,dirlist,filelist in os.walk(config['local_path']+'/'+yesterday_date):  
        for file in filelist:  
            fn = os.path.join(pathstr,file)
            file_list.append(fn)

def update_file(ssh,sftp,file_list,yesterday_date,begin):
    '''
        向服务器上传文件
        并反馈上传结果
    '''
    update_file_num = 0  
    
    for item in file_list:   
        local_file_path = item
        target_file_path = config['ssh_path']+yesterday_date+'/'+item.split('/')[-1]    
        update_file_num = update_file_num + check_file( ssh, sftp, local_file_path, target_file_path)  
    end = datetime.datetime.now()  
    print('本次上传结束：更新文件%s个，耗时：%s' % ( update_file_num, end-begin)) 
    #返回是否更新了服务器文件 （若更新的文件数为0，则今日不在执行上传与检测操作）
    return update_file_num == 0

def main():
    flag_trans_complete = False
    while True:
        # 获取日期以用于命名文件夹
        yesterday_date = yesterday()
        # 显示当前上传任务
        print ('今日文件上传' + ('已完成' if flag_trans_complete ==True else '未完成'))

        if int(time.strftime("%H%M%S"))> config['SYNC trigger time'] and flag_trans_complete == False:
            # 上传流程开始  
            print('上传开始')  
            begin = datetime.datetime.now()

            # ssh控制台
            ssh = paramiko.SSHClient()  
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())    
        
            ssh.connect(hostname=config['hostname'], port=config['port'],  
                username=config['username'], password=config['password'])  
        
            # ssh传输  
            transport = paramiko.Transport((config['hostname'],config['port']))  
        
            transport.connect(username=config['username'],password=config['password'])  
        
            sftp = paramiko.SFTPClient.from_transport(transport)


            # 本地与远程文件列表  
            file_list = []   
            ssh_file_list = []
            get_local_path(file_list,yesterday_date) 
            print (file_list)
            check_remote_directory(ssh, ssh_file_list,yesterday_date)
            #若更新的文件数为0，则今日不在执行上传与检测操作
            if update_file(ssh,sftp,file_list,yesterday_date,begin) : 
                flag_trans_complete=True 

            # 关闭连接  
            sftp.close()  
            ssh.close()  

        if int(time.strftime("%H%M%S")) > config['delete trigger time'] and flag_trans_complete == True :
            my_file = config['local_path']+'/'+yesterday_date
            if os.path.exists(my_file):
                shutil.rmtree(my_file)
                print ("成功删除本地文件"+my_file)

        if time.localtime()[3] < 1 :
            flag_trans_complete = False

        time.sleep(config['sleep seconds'])



if __name__ == "__main__":
    main()
  
