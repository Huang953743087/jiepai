#!/usr/bin/env python3
#-*- coding: utf-8 -*-
import re
from hashlib import md5
from urllib.parse import urljoin
from multiprocessing import Pool
import pymongo



from config import *
import os
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException


client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]


#解析首页地址，为对抗反扒添加请求header，返回获得的html
def get_page_index(url, num):
    headers={'Referer':'http://www.mm131.com/qingchun/',
             'Accept - Language': 'zh - CN, zh;q = 0.9',
            'Connection':'keep-alive',
             'Accept - Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:43.0) Gecko/20100101 Firefox/43.0'}
    try:
        session = requests.session()
        session.get('http://www.mm131.com/qingchun/')
        print(url+'当前为第%d'%num)
        response = session.get(url, headers=headers)
        response.encoding ='gbk'
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('获取图集列表失败，当前为第%d页'%num)
        return None


#解析索引页html，获得每页url并返回
def parse_page_index(text):
    url_pattern = re.compile('<dd><a target="_blank" href="(.*?)"><img src')
    urls = re.findall(url_pattern, text)
    return urls


#获得每页源码并进行解析，解析出图片地址并进行保存，同时返回字典存储title与images地址
def get_and_parse_page_datail(url):
    #不添加referer无法获取图片
    headers = {'Referer':'http://www.mm131.com/qingchun/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36'}
    images=[]
    #图片页源码有多重，所以提供2种正则
    images_pattern1 = re.compile(r'class="content-pic.*?a href=.(.*?).><img alt=".*?" src="(.*?)" /></a></div>', re.S)
    images_pattern2 = re.compile(r'class="content-pic.*?a href=.(.*?).><img src="(.*?)" alt=".*?" /></a></div>', re.S)
    title_soup = requests.get(url, headers=headers)
    title_soup.encoding = 'gbk'
    if title_soup.status_code == 200:
        soup = BeautifulSoup(title_soup.text, 'lxml')
        title = soup.select('title')[0].get_text()
    while True:
        try:
            response = requests.get(url, headers=headers)
            response.encoding = 'gbk'
            if response.status_code == 200:
                url_and_image = re.search(images_pattern1, response.text)
                if url_and_image is None:
                    url_and_image = re.search(images_pattern2,response.text)
                if url_and_image is None:
                    print(url+"源码匹配失败，请查看")
                    return None
                images.append(url_and_image.group(2))
                #下载图片并进行保存
                download_image(url_and_image.group(2), title)
                if len(url_and_image.group(1)) < 15:
                    url = urljoin(url, url_and_image.group(1))
                else:
                    result = {
                        'title':title,
                        'images': images,
                    }
                    return result
        except RequestException:
            print('获取图详情失败，当前为第%s' %url)
            return None


#下载图片
def download_image(url,title):
    print('Downloading', url)
    headers = {'Referer':'http://www.mm131.com/qingchun/',
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36'}
    try:
        response = requests.get(url, headers = headers)
        if response.status_code == 200:
            save_image(response.content,title)
        return None
    except ConnectionError:
        return None


#保存图片
def save_image(content,title):
    file_title = 'G:/spiderdownload/'+title
    is_Exists = os.path.exists(file_title)
    if not is_Exists:
        # 如果不存在则创建目录
        # 创建目录操作函数
        os.makedirs(file_title)
        print(file_title + ' 创建成功')
    file_path = "{0}/{1}.jpg".format(file_title, md5(content).hexdigest())
    print(file_path)
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
                f.write(content)
                f.close()


#保存到mongoDB数据库
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('Successfully Saved to Mongo', result)
        return True
    return False


def main(url,i):

    text = get_page_index(url, i)
    urls = parse_page_index(text)
    for url in urls:
            result = get_and_parse_page_datail(url)
            if result:
                save_to_mongo(result)


if __name__ == '__main__':
    url = 'http://www.mm131.com/qingchun/'
    for i in range(13, 32):
        url_end = ('list_1_%d.html' %i )
        url = urljoin(url, url_end)
        main(url,i)
