from socket import *
import threading
import os
import sys
import time
import pickle
import datetime


#设置禁止访问文件的列表
def setforbiddenlist():
    forbidden_filename_list = ["a.txt"]
    with open("forbiddenlist.txt", 'wb') as f:
        pickle.dump(forbidden_filename_list, f)


#获取禁止访问文件的列表
def getforbiddenlist():
    forbidden_filename_list = list()
    with open("forbiddenlist.txt", 'rb') as f:
        forbidden_filename_list = pickle.load(f)

    return forbidden_filename_list


#初始化socket
def init():
    setforbiddenlist()
    global serverSocket

    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    #使用http://localhost:5678/来访问
    serverPort = 5678
    serverSocket.bind(('', serverPort))
    serverSocket.listen(5)

    print('Ready to serve')


#将http请求解析为字典并返回
def parse_httpheader(http_msg):
    raw_list = http_msg.split('\r\n')
    request = {}
    for index in range(1, len(raw_list)):
        item = raw_list[index].split(":", 1)
        if len(item) == 2:
            request.update({item[0].lstrip(' '): item[1].lstrip(' ')})
    filename = http_msg.split()[1]
    request.update({'filename': filename})

    return request

#设置返回文件的类型
def set_content_type(filename):
    Content_Type = ""
    filename_extension =filename.split('.')[1]
    if filename_extension == 'html':
        Content_Type = "Content-Type: text/html;charset=utf-8\r\n"
    elif filename_extension == 'txt':
        Content_Type = "Content-Type: text/plain;charset=utf-8\r\n"
    else:
        Content_Type = "Content-Type: text/html;charset=utf-8\r\n"

    return  Content_Type



#响应http请求
def msg_handle(connectionSocket, addr, forbiddenlist):

    #使用异常机制, 若发生IOError则文件读取异常, 捕获异常实现404状态码
    try:
        print('A client connected ...', threading.get_ident())

        http_msg = connectionSocket.recv(2048).decode()
        request = parse_httpheader(http_msg)

        #获取请求的文件名称
        filename = request['filename'][1:]
        #若请求 / 则返回index.html
        if len(filename) == 0:
            filename = 'index.html'

        #读取请求文件的最后修改时间
        time_last_modified = time.localtime(os.path.getmtime(filename))
        timestr = time.strftime("%a, %d %b %Y %H:%M:%S", time_last_modified)
        datetime_last_modified = datetime.datetime.strptime(timestr, "%a, %d %b %Y %H:%M:%S")
        timemsg = "Last-Modified: " + timestr + "\r\n"

        #判断请求文件是否forbidden
        forbiddenflag = False
        sendfileflag = True
        for item in forbiddenlist:
            if filename == item:
                forbiddenflag = True
                break

        #实现403状态码
        if forbiddenflag:
            sendfileflag = False
            fbdmsg = 'HTTP/1.1 403 Forbidden \r\n\r\n'
            connectionSocket.send(fbdmsg.encode())
            connectionSocket.send("<html><head></head><body><h1>403 Forbidden</h1></body></html>\r\n".encode())
            connectionSocket.close()

        #实现304状态码
        if request.get('If-Modified-Since', "-1") != "-1":

            datetime_if_modified_since = datetime.datetime.strptime(request['If-Modified-Since'], "%a, %d %b %Y %H:%M:%S")
            if( datetime_last_modified-datetime_if_modified_since).seconds <= 0:
                print("set flag flase")
                sendfileflag = False
                not_modified_304_msg = "HTTP/1.1 304 Not Modified \r\n"
                finalmsg = not_modified_304_msg +  timemsg + "\r\n"
                connectionSocket.send(finalmsg.encode())
                connectionSocket.close()


        #实现200状态码
        if sendfileflag:
            f = open(filename, encoding='utf-8')

            outputdata = f.readlines()
            OK_200_msg = "HTTP/1.1 200 OK \r\n"
            Content_Type = set_content_type(filename)
            finalmsg = OK_200_msg + timemsg + Content_Type +"\r\n"
            connectionSocket.send(finalmsg.encode())
            # Send the content of the requsted file to the Client
            for i in range(0, len(outputdata)):
                connectionSocket.send(outputdata[i].encode('utf-8'))
            connectionSocket.send("\r\n".encode())
            connectionSocket.close()

    except IOError:
        err_msg = 'HTTP/1.1 404 Not Found \r\n\r\n'
        connectionSocket.send(err_msg.encode())
        connectionSocket.send("<html><head></head><body><h1>404 Not Found</h1></body></html>\r\n".encode())
        connectionSocket.close()


def accept_client():
    while True:
        connectionSocket, addr = serverSocket.accept()
        forbiddenlist = getforbiddenlist()
        cthread = threading.Thread(target=msg_handle, args=(connectionSocket, addr, forbiddenlist))
        cthread.start()


if __name__ == '__main__':
    init()
    mainthread = threading.Thread(target = accept_client())
    mainthread.start()
    sys.exit()