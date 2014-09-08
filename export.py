#! /usr/bin/python
# -*- coding: utf-8 -*-

import collections
import lxml.html
import os
import os.path
import requests
import sys
import time

class Crawler(object):

    def __init__(self, root):
        self.__root = root
        self.__urls = set([root])
        self.__queue = collections.deque([root])
        self.__visited = []
        self.__canonical = {}

    def __enqueueUrls(self, document, tag, attribute):
        tags = document.findall('.//%s' % tag)
        for tag in tags:
            url = tag.attrib.get(attribute)
            if url and url.startswith(self.__root):
                url = url.split('#')[0]
                if url not in self.__urls:
                    self.__urls.add(url)
                    self.__queue.append(url)

    def __parse(self, url, html):
        document = lxml.html.document_fromstring(html)
        rels = document.findall('.//link[@rel=\'canonical\']')
        assert len(rels) <= 1
        if rels:
            self.__canonical[url] = rels[0].attrib['href']
            if url != self.__canonical[url]:
                url = self.__canonical[url]
                if url in self.__urls:
                    return None
                self.__urls.add(url)
        self.__enqueueUrls(document, 'a', 'href')
        self.__enqueueUrls(document, 'img', 'src')
        self.__enqueueUrls(document, 'link', 'href')
        self.__enqueueUrls(document, 'script', 'src')
        return url

    def __crawl(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            if response.headers['content-type'].startswith('text/html'):
                url = self.__parse(url, response.text)
                if not url:
                    return
            self.__visited.append(url)
            self.__write(url, response.content)
        else:
            print >> sys.stderr, 'Unable to crawl "%s"' % url

    def __getPath(self, url):
        return ''.join(url.split('://')[1:])

    def __write(self, url, content):
        path = self.__getPath(url)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        if path[-1] == '/':
            path += 'index.html'
        with open(path, 'wb') as output:
            output.write(content)

    def __writeCanonicals(self):
        with open(self.__getPath(self.__root + '.htaccess'), 'w') as output:
            output.write('RewriteEngine on\n')
            for url, canonical in self.__canonical.iteritems():
                output.write('RewriteRule ^/%s$ %s\n' % (self.__getPath(url), canonical))

    def __displayProgress(self):
        sys.stdout.write('\r%i found, %i visited, %i non-canonical, %i left' % (len(self.__urls), len(self.__visited), len(self.__canonical), len(self.__queue)))
        sys.stdout.flush()

    def crawl(self):
        while self.__queue:# and len(self.__visited) < 5:
            self.__displayProgress()
            time.sleep(1)
            self.__crawl(self.__queue.popleft())
        self.__displayProgress()
        print
        self.__writeCanonicals()

if __name__ == '__main__':
    crawler = Crawler('http://rtfblog.com/')
    crawler.crawl()
