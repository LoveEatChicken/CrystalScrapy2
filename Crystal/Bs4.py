#ii!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Crystal'

from bs4 import BeautifulSoup
import re

h = '<a href="//list.jd.com/list.html?cat=1316,1381,1392&amp;ev=exbrand_7928" clstag="shangpin|keycount|product|pinpai_2" target="_blank">韩后</a>'
soup = BeautifulSoup(h,"html5lib",from_encoding='utf-8')
print soup.text

