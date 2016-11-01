# -*- coding: utf-8 -*-

import json
from scrapy.exporters import JsonLinesItemExporter

class DecodeJsonLinesItemExporter(JsonLinesItemExporter):
    """中文解码JSON LINE"""


    def export_item(self, item):
        itemdict = dict(self._get_serialized_fields(item))
        data = self.encoder.encode(itemdict) + '\n'
        self.file.write(data.decode('unicode_escape'))