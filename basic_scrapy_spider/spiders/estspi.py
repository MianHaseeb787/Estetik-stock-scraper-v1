import scrapy
import gspread
from basic_scrapy_spider.items import EstItem
# from googletrans import Translator, LANGUAGES
import json
from googleapiclient import discovery
from google.oauth2 import service_account
import base64
from email.message import EmailMessage
import google.auth
# from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re


scopes = [
    'https://www.googleapis.com/auth/spreadsheets', 
    'https://www.googleapis.com/auth/drive',
    'https://mail.google.com/' 
]
creds = service_account.Credentials.from_service_account_file("credentials.json", scopes=scopes)


client = gspread.authorize(creds)

sheet_id = "1hpu0tgLUlEtEFZ2i6DM61iG9M2TjIoZU_2thj7C4XLQ"

sheet = client.open_by_key(sheet_id)
worksheet = sheet.get_worksheet(0)

class QuotesSpider(scrapy.Spider):
    name = 'est'
    # custom_settings = {
    #     'FEED_FORMAT': 'csv',
    #     'FEED_URI': 'output.csv'
    # }
    # allowed_domains = ['quotes.toscrape.com']
    # start_urls = ['http://quotes.toscrape.com/']
    exchange_rate = 0
    gsheet_rows = []

    # row_count = 1


    def start_requests(self):
        exchange_api_url = "https://api.freecurrencyapi.com/v1/latest?apikey=fca_live_SmuB3TpaaedcTgN1EvsAO5f14ZxuKBTX8ckWd9cX&currencies=EUR&base_currency=PLN"
        yield scrapy.Request(exchange_api_url, callback=self.get_exchangeRate)

    def get_exchangeRate(self, response):
        api = json.loads(response.body)
        self.exchange_rate = api.get("data", {}).get("EUR")
        

        start_url = "https://estetik.pl/"
        yield scrapy.Request(url=start_url, callback=self.parse)


    def parse(self, response):
        all_cats =  response.css('.menu-list > li.parent')

        for cat in all_cats:
            cat_link = cat.css('span.h3 > a::attr(href)').get()
            cat_full_link = "https://estetik.pl" + cat_link
            # if cat == all_cats[1]:
            #     break
            
            yield scrapy.Request(cat_full_link, headers={'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'}, callback=self.cat_page)
    
    def cat_page(self, response):
        products = response.css('.product-main-wrap')

        for product in products:
            product_link =  product.css('.product-main-wrap > a::attr(href)').get()
            product_full_link = "https://estetik.pl" + product_link 

            # if product == products[10]:
            #     break
            

            yield scrapy.Request(product_full_link, headers={'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'} , callback=self.parse_each_product)
        
        next_url = response.css('ul.paginator > li.selected +li +li >a::attr(href)').get() 
        print(next_url)
        print("NEEEEEEEXXXXXXXXTTTTTTTTTTTTT URRRRLLLLLLLLL")
        if  next_url is not None:

            next_full_url = "https://estetik.pl" + next_url

            print("NEEEEEEEXXXXXXXXTTTTTTTTTTTTT URRRRLLLLLLLLL")
            print(next_full_url)

            yield scrapy.Request(url=next_full_url, callback=self.cat_page)

    def parse_each_product(self, response):

        item =  EstItem()

        availability_pi =  response.css('.main-product__details-row.availability > span:nth-child(2)::text').get().strip(),
        # availability_en =  translate_polish_to_english(availability_pi)

        # pd_pl = response.css('.description-box__inner.innerbox > div.resetcss').extract()

        # # Joining HTML elements into a single string
        # pd_pl_text = ' '.join(pd_pl)

        sale_price = response.css('.main-price.color::text').get()
        
        regular_price = response.css('.main-price::text').get()
        sale_reg_price = response.css('div.price > del::text').get()

        stock = ""
        if 'Dostępny' in availability_pi:
            stock = "instock"
        else:
            stock = "outofstock"


        


        regular_price_afterEx = ""
        sale_price_afterEx = ""
        if sale_price is not None:
            # own regular price
            
            if sale_price is not None:

                if '\xa0' in sale_price:
                    sprice_text_cleaned = sale_price.replace('\xa0', '').replace(',', '.')

                    try:

                        sale_price_fix = sprice_text_cleaned.replace('zł', '').replace(',', '.')
                        sale_price_aex =  float(sale_price_fix) * self.exchange_rate
                        sale_price_afterEx = format(sale_price_aex, ".2f")

                        # Profit 30%
                        sale_price_afterEx = float(sale_price_aex)
                        sale_price_increase = sale_price_afterEx * 0.3
                        sale_price_afterEx = sale_price_afterEx + sale_price_increase

                        sale_price_afterEx = format(sale_price_afterEx, ".2f")
                        
                    except Exception as e:
                        sale_price_afterEx = ""
                        print(f"Error occurred during conversion: {e}")

                else: 

                    try:

                        sale_price_fix = sale_price.replace('zł', '').replace(',', '.')
                        sale_price_aex =  float(sale_price_fix) * self.exchange_rate
                        sale_price_afterEx = format(sale_price_aex, ".2f")


                        sale_price_afterEx = float(sale_price_aex)
                        sale_price_increase = sale_price_afterEx * 0.3
                        sale_price_afterEx = sale_price_afterEx + sale_price_increase

                        sale_price_afterEx = format(sale_price_afterEx, ".2f")


                    except Exception as e:
                        sale_price_afterEx = ""
                        print(f"Error occurred during conversion: {e}")

                if sale_reg_price is not None:
                    if '\xa0zł' in sale_reg_price:
                        sale_reg_price =  sale_reg_price.replace("\xa0zł", "").replace(",", ".")

                        try:

                            sale_reg_aex =  float(sale_reg_price) * self.exchange_rate
                            sale_reg_afterEx = format(sale_reg_aex, ".2f")


                            regular_price_afterEx = sale_reg_afterEx
                            regular_price_afterEx = float(regular_price_afterEx)

                            regular_price_increase = regular_price_afterEx * 0.3
                            regular_price_afterEx = regular_price_afterEx + regular_price_increase

                            regular_price_afterEx = format(regular_price_afterEx, ".2f")
                            
                        except Exception as e:
                            regular_price_afterEx =  ""
                    else:
                        regular_price_afterEx =  ""
                    

            
        else:
           
            if regular_price is not None:

                if '\xa0' in regular_price :
                    # Remove non-breaking space and replace comma with dot
                    price_text_cleaned = regular_price.replace('\xa0', '').replace(',', '.')


                    regular_price_fix = price_text_cleaned.replace('zł', '').replace(',', '.')
                    
                    try:
                        regular_price_aex = float(regular_price_fix) * self.exchange_rate
                        regular_price_afterEx = format(regular_price_aex, ".2f")

                        regular_price_afterEx = float(regular_price_afterEx)

                        r_price_increase = regular_price_afterEx * 0.3
                        regular_price_afterEx = regular_price_afterEx + r_price_increase

                        regular_price_afterEx = format(regular_price_afterEx, ".2f")
                    except Exception as e:
                        print(f"Error occurred during conversion: {e}")
                        regular_price_afterEx = ""
                else:
                
                    regular_price_fix = regular_price.replace('zł', '').replace(',', '.')
                    
                    try:
                        regular_price_aex = float(regular_price_fix) * self.exchange_rate
                        regular_price_afterEx = format(regular_price_aex, ".2f")

                        print("Regularrr Priceeee before .3333")
                        print(regular_price_afterEx)

                        regular_price_afterEx = float(regular_price_afterEx)

                        r_price_increase = regular_price_afterEx * 0.3
                        regular_price_afterEx = regular_price_afterEx + r_price_increase
                        regular_price_afterEx = format(regular_price_afterEx, ".2f")

                        print("Regularrr Priceeee afterrrrr .3333")
                        print(regular_price_afterEx)

                    except Exception as e:
                        print(f"Error occurred during conversion: {e}")
                        regular_price_afterEx = ""



        item =  EstItem()


        # item['rnum'] = self.row_count
        
        item['name'] = response.css('.name::text').get().strip()

        product_code = response.css('.main-product__details-row.code > span::text').get()
        if product_code:
            product_code = re.sub(r'_outlet$', '', product_code, flags=re.IGNORECASE)  # Remove "_OUTLET" (case-insensitive)
        item['productCode'] = product_code
        item['stock'] = stock
        
        item['salePrice'] = sale_price_afterEx
        item['regularPrice'] = regular_price_afterEx
        
        # item = {
        # 'rnum' : self.row_count,
        # 'name' : response.css('.name::text').get().strip(),
        # 'productCode' : response.css('.main-product__details-row.code > span::text').get(),
        # 'stock' : stock,
        
        # 'salePrice' : sale_price_afterEx,
        # 'regularPrice' : regular_price_afterEx
        # }

        # yield item
        self.gsheet_rows.append(item)
        print(item)
        # print(self.gsheet_rows)
        
        # yield item
        

    def closed(self, reason):
        print("Closed")

        # Remove duplicates based on 'name' and 'productCode' (or other fields if needed)
        unique_rows = []
        seen = set()
        for row in self.gsheet_rows:
            unique_key = (row.get('name', ''), row.get('productCode', ''))  # Tuple of unique identifiers
            if unique_key not in seen:
                seen.add(unique_key)
                unique_rows.append(row)

        self.gsheet_rows = unique_rows

        headers = ['Name', 'Product code', 'Stock',  'RegularPrice', 'SalePrice']
        worksheet.insert_row(headers, index=1)

        data_to_write = []
        for row in self.gsheet_rows:
            data_to_write.append([row.get('name', ''), row.get('productCode', ''), row.get('stock', ''), 
                                row.get('regularPrice', ''), row.get('salePrice', '')])

       
        range_name = 'A2:F'  
        request_body = {
            'value_input_option': 'USER_ENTERED',  
            'data': [
                {
                    'range': range_name,  
                    'values': data_to_write,  
                }
            ]
        }
        service = discovery.build('sheets', 'v4', credentials=creds)
        response = service.spreadsheets().values().batchUpdate(spreadsheetId=sheet.id, body=request_body).execute()

       
        print(response)
        print(reason)

