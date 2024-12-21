# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


# class EstItem(scrapy.Item):

#     # rnum = scrapy.Field()
#     name = scrapy.Field()
#     productCode = scrapy.Field()
#     stock = scrapy.Field()
#     regularPrice = scrapy.Field()
#     salePrice = scrapy.Field()

class EstItem(scrapy.Item):
    # define the fields for your item here like:
    ID = scrapy.Field()
    name = scrapy.Field()
    category = scrapy.Field()
    productCode = scrapy.Field()
    stock = scrapy.Field()
    tags = scrapy.Field()
    availability = scrapy.Field()
    regularPrice = scrapy.Field()
    salePrice = scrapy.Field()
    imageUrl = scrapy.Field()
    productDesp = scrapy.Field()
    ourRPrice = scrapy.Field()
    ourSPrice =  scrapy.Field()

    
