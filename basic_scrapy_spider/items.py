# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class EstItem(scrapy.Item):

    # rnum = scrapy.Field()
    name = scrapy.Field()
    productCode = scrapy.Field()
    stock = scrapy.Field()
    regularPrice = scrapy.Field()
    salePrice = scrapy.Field()

    
