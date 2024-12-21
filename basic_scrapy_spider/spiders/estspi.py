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
import time
from bs4 import BeautifulSoup


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
    scraped_data = []

    # row_count = 1
    # scraped_data = worksheet.get_all_records(expected_headers=['ID',	'Name', 	'Product code',	'Stock',	'Our Price', 'RegularPrice',	'SalePrice',	'Description',	'Categories',	'Tags',	'Images'])
    print(f"Lenght of scraped data : {len(scraped_data)}")


    def start_requests(self):
        exchange_api_url = "https://api.freecurrencyapi.com/v1/latest?apikey=fca_live_SmuB3TpaaedcTgN1EvsAO5f14ZxuKBTX8ckWd9cX&currencies=EUR&base_currency=PLN"

        yield scrapy.Request(exchange_api_url, callback=self.get_exchangeRate)

    def get_exchangeRate(self, response):
        api = json.loads(response.body)
        self.exchange_rate = api.get("data", {}).get("EUR")
        

        login_url = "https://estetik.pl/pl/login"

        form_data = {
            'mail' : 'info@aestheticmedicine.ie',
            'pass' : 'LCPLrUAg!3h!Azq'
        }
        yield scrapy.FormRequest(url=login_url, formdata=form_data, callback=self.parse)


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
        if  next_url is not None:

            next_full_url = "https://estetik.pl" + next_url
            yield scrapy.Request(url=next_full_url, callback=self.cat_page)
        
        # else:



    def parse_each_product(self, response):

        item =  EstItem()

        availability_pi =  response.css('.main-product__details-row.availability > span:nth-child(2)::text').get().strip(),
        # availability_en =  translate_polish_to_english(availability_pi)

        pd_pl_elements = response.css('.description-box__inner.innerbox > div.resetcss > *').extract()


        # Initialize an empty string to combine the text
        combined_text = ""

        # Parse each element with BeautifulSoup and extract text
        for element in pd_pl_elements:
            soup = BeautifulSoup(element, "html.parser")
            soup = str(soup)
            combined_text += soup
            # combined_text += soup.get_text(strip=True) + "\n"  # Add a line break between texts

        # Strip any trailing newline from the final text
        pd_pl = combined_text.strip()
        print(f"desp  ;;;;;   :::::::::::: {pd_pl}")

        image_url = "https://estetik.pl" + response.css('.photo::attr(src)').get()


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

        cat1 = response.css('li.bred-2 >a span:nth-child(2)::text').get().strip()
        cat2 = response.css('.bred-4 .raq+ span ::text').get()
        category =  f'{cat1},{cat1} > {cat2}'

        regular_price_afterEx = ""
        sale_price_afterEx = ""
        sale_price_fix = ""
        regular_price_fix = ""
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
                        regular_price_fix = sale_reg_price

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
        
        name =  response.css('.name::text').get().strip()
        product_code = response.css('.main-product__details-row.code > span::text').get()
        if 'uszkodzone opakowanie' not in name and 'termin ważności' not in name and product_code != '551E-53976' and product_code != '184E-59583' and product_code != '486E-83779' and product_code != '709E-47767' and product_code != '233E-93177':
                
            item['name'] = name
            # product_code = response.css('.main-product__details-row.code > span::text').get()
            # Check for "_OUTLET" and skip adding to `self.gsheet_rows` if present
            

            if product_code and re.search(r'_outlet$', product_code, flags=re.IGNORECASE):
                print(f"Skipping product with code: {product_code}")
            else:
                # Process product data as usual
                # if product_code:
                    # product_code = re.sub(r'_outlet$', '', product_code, flags=re.IGNORECASE)  # Remove "_OUTLET"

                # Populate item fields
                item['productCode'] = product_code
                item['stock'] = stock
                item['tags'] = response.css('.main-product__details-row.manufacturer > a ::text').get().strip()
                item['availability'] = availability_pi
                item['imageUrl'] = image_url
                item['productDesp'] = pd_pl
                item['salePrice'] = sale_price_fix
                item['regularPrice'] = regular_price_fix
                item['ourRPrice'] = regular_price_afterEx
                item['ourSPrice'] = sale_price_afterEx
                item['category'] = category

                # Add to `self.gsheet_rows`
                self.gsheet_rows.append(item)

  
        

    def closed(self, reason):
        creds = service_account.Credentials.from_service_account_file("credentials.json", scopes=scopes)


        client = gspread.authorize(creds)

        sheet_id = "1hpu0tgLUlEtEFZ2i6DM61iG9M2TjIoZU_2thj7C4XLQ"

        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.get_worksheet(0)
    


        print("Closed")
        print("All products scrapped")
        # scraped_data = worksheet.get_all_values()  # Fetch data as a list of dictionaries
        try:
            products_codes = worksheet.col_values(3)  # Assuming column 3 contains product codes
        except:
            time.sleep(60)
            products_codes = worksheet.col_values(3)

        # Iterate in reverse order
        for row_index in range(len(products_codes) - 1, 0, -1):
            products_code = products_codes[row_index]
            matching_product = next(
                (item for item in self.gsheet_rows if item.get('productCode') == products_code), None
            )
            if matching_product is None:
                worksheet.delete_rows(row_index + 1)

                print("product Delted from Google sheet")
        
        # Get the product codes from the cleaned Google Sheet
        try:
            remaining_product_codes = worksheet.col_values(3)[1:]  # Column 3: Product codes
        except:
            time.sleep(60)
            remaining_product_codes = worksheet.col_values(3)[1:] 

        # Create a dictionary for quick lookup from gsheet_rows
        gsheet_data_dict = {row['productCode']: row for row in self.gsheet_rows}

        # Prepare the aligned data in the same order as the Google Sheet
        aligned_data = []

        for product_code in remaining_product_codes:
            # Fetch the matching row from gsheet_rows
            matching_product = gsheet_data_dict.get(product_code, {})
            aligned_data.append({
                'productCode': product_code,
                'regularPrice': matching_product.get('regularPrice', ''),
                'salePrice': matching_product.get('salePrice', ''),
                'stock': matching_product.get('stock', ''),
                'ourRPrice' : matching_product.get('ourRPrice', ''),
                'ourSPrice' : matching_product.get('ourSPrice', '')
            })
        
        regular_prices = [row['regularPrice'] for row in aligned_data]
        sale_prices = [row['salePrice'] for row in aligned_data]
        stocks = [row['stock'] for row in aligned_data]

        # Prepare the data to write in the required format
        data_to_write = [[row['productCode'], row['stock'], row['regularPrice'], row['salePrice'], row['ourRPrice'], row['ourSPrice']] for row in aligned_data]
       

        # Define the range for updating
        range_name = 'D2:I'  # Assuming columns C (productCode), D (stock), E (regularPrice), F (salePrice)

        # Prepare the request body for batch update
        request_body = {
            'value_input_option': 'USER_ENTERED',
            'data': [
                {
                    'range': range_name,
                    'values': data_to_write,
                }
            ]
        }

        # Execute the batch update
        try:
            service = discovery.build('sheets', 'v4', credentials=creds)
            response = service.spreadsheets().values().batchUpdate(spreadsheetId=sheet.id, body=request_body).execute()
        except:
            time.sleep(60)
            service = discovery.build('sheets', 'v4', credentials=creds)
            response = service.spreadsheets().values().batchUpdate(spreadsheetId=sheet.id, body=request_body).execute()

        time.sleep(60)


        #### new products
        existing_product_codes = set(remaining_product_codes)

        # Filter out products already in Google Sheet
        new_products = [row for row in self.gsheet_rows if row['productCode'] not in existing_product_codes]

        for new_product in new_products:
            p_code = new_product['productCode']
            print("***************************")
            print(p_code)

        # At this point, `new_products` contains only products not in the Google Sheet
        self.gsheet_rows = new_products
        print(f"lenght of new products : {len(new_products)}")

        from gspread_formatting import format_cell_range, CellFormat, Color

        # Get the last product ID from the sheet
        try:
            product_ids = worksheet.col_values(1)[1:]  # Assuming product ID is in column 1, skipping header
        except:
            time.sleep(60)
            product_ids = worksheet.col_values(1)[1:] 

        last_product_id = int(product_ids[-1]) if product_ids else 0
        print(f"Last Product Id : {last_product_id}")

        # Assign IDs to new products incrementally
        new_products_ids = []
        for index, product in enumerate(new_products, start=1):
            product_id = last_product_id + index
            new_products_ids.append(product_id)

        # Prepare data to write in the specified order
        data_to_write_new = [
            [
                new_products_ids[i],                  # ID
                product.get('name', ''),       # Name
                product.get('productCode', ''),  # Product code
                product.get('productCode', ''),  # Product code
                product.get('stock', ''),      # Stock
                product.get('regularPrice', ''),  # Regular price
                product.get('salePrice', ''),  # Sale price
                product.get('ourRPrice', ''),  # Our regular price
                product.get('ourSPrice', ''),  # Our sale price
                product.get('productDesp', ''),  # Description
                product.get('category', ''),
                product.get('tags', ''),       # Tags
                product.get('imageUrl', '')    # Images
            ]
            for i, product in enumerate(new_products)
        ]

        # Define the range for the batch update (add to the end of the sheet)
        try:
            last_row = len(worksheet.get_all_values()) + 1  # Calculate the row index for appending
        except:
            time.sleep(60)
            last_row = len(worksheet.get_all_values()) + 1 

        range_name = f'A{last_row}:M'  # Target columns for new products

        # Batch update request
        request_body = {
            'value_input_option': 'USER_ENTERED',
            'data': [
                {
                    'range': range_name,
                    'values': data_to_write_new,
                }
            ]
        }



        # Execute the batch update
        service = discovery.build('sheets', 'v4', credentials=creds)
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=worksheet.spreadsheet.id, body=request_body
        ).execute()


        # Apply green color to the first new product row
        if new_products:
            green_color = Color(red=0.8, green=1.0, blue=0.8)  # Light green
            green_format = CellFormat(backgroundColor=green_color)
            first_new_row = last_row

            # Apply the color only to the first newly added row
            format_cell_range(
                worksheet,
                f'A{first_new_row}:M{first_new_row}',  # Adjust to include relevant columns
                green_format
            )

        print(f"Added {len(new_products)} new products. First new product highlighted in green.")
        time.sleep(60)



        # request body for new sheet
        client = gspread.authorize(creds)
        sheet_id = "1fKnb0-F6dfqU_FUpNFPw7WZcasma9VY1OSPAI-YUuO8"
        sheet = client.open_by_key(sheet_id)
        new_products_sheet = sheet.get_worksheet(0)
        # worksheet1 = sheet.worksheet('NewProducts')
        try:
            last_row_new_sheet = len(new_products_sheet.get_all_values()) + 1 
        except:
            time.sleep(60)
            last_row_new_sheet = len(new_products_sheet.get_all_values()) + 1 

        range_name_new_sheet = f'A{last_row_new_sheet}:M'  # Target columns for new products

        # Batch update request
        request_body_new_sheet = {
            'value_input_option': 'USER_ENTERED',
            'data': [
                {
                    'range': range_name_new_sheet,
                    'values': data_to_write_new,
                }
            ]
        }



        service = discovery.build('sheets', 'v4', credentials=creds)
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=new_products_sheet.spreadsheet.id, body=request_body_new_sheet
        ).execute()
        print("done")
        print(f"worksheet title : {worksheet.title}")
        print(f"worksheet 1 title : {new_products_sheet.title}")


        # # Iterate through rows in the Google Sheet
        # for row_index, row in enumerate(self.scraped_data, start=2):  # Start from 2 to match Google Sheets row numbering
        #     print(f"Row index : {row_index}")
        #     g_product_id = row.get('ID')
        #     g_product_code = row.get('Product code')
        #     g_stock = row.get('Stock')
        #     g_product_price = row.get('RegularPrice')
        #     g_sale_price = row.get('SalePrice')

            

        #     if g_product_id and g_product_code:
        #         # Search for a matching product in self.gsheet_rows
        #         matching_product = next((item for item in self.gsheet_rows 
        #                                 if item.get('productCode') == g_product_code), None)

        #         if matching_product:
        #             # Update stock, sale price, and regular price in the sheet
        #             print("product matched")

        #             stock = matching_product.get('stock', '')
        #             sale_price = matching_product.get('salePrice', '')
        #             regular_price = matching_product.get('regularPrice', '')

        #             print(f"g_stock : {g_stock}..stock : {stock} & g_price : {g_product_price}.. price : {regular_price} & g_sale_price : {g_sale_price} .. sale price : {sale_price}")

        #             if str(g_stock).strip() == str(stock).strip() and \
        #             str(g_product_price).strip() == str(regular_price).strip() and \
        #             str(g_sale_price).strip() == str(sale_price).strip():
        #                 print("continuing")
        #                 continue
                    

        #             data_to_update = [[stock, regular_price, sale_price]]

        #             # Assuming `row_index` is the row to update
        #             worksheet.update(f"D{row_index}:F{row_index}", data_to_update)
        #             time.sleep(3)

        #             # Remove the matching product from gsheet_rows
        #             self.gsheet_rows.remove(matching_product)
        #         else:
        #             # If no matching product, delete the row from the Google Sheet
        #             worksheet.delete_rows(row_index)
        #             print(f"Row with ProductId: {g_product_id} and productCode: {g_product_code} deleted")
        #     else:
        #         print("new product")

        # print(f"kenght of the scraped data : {len(self.gsheet_rows)}")

        #####


        # # Remove duplicates based on 'name' and 'productCode' (or other fields if needed)
        # unique_rows = []
        # seen = set()
        # for row in self.gsheet_rows:
        #     unique_key = (row.get('name', ''), row.get('productCode', ''))  # Tuple of unique identifiers
        #     if unique_key not in seen:
        #         seen.add(unique_key)
        #         unique_rows.append(row)

        # self.gsheet_rows = unique_rows

        # headers = ['Name', 'Product code', 'Stock',  'RegularPrice', 'SalePrice']
        # worksheet.insert_row(headers, index=1)

        # data_to_write = []
        # for row in self.gsheet_rows:
        #     data_to_write.append([row.get('name', ''), row.get('productCode', ''), row.get('stock', ''), 
        #                         row.get('regularPrice', ''), row.get('salePrice', '')])

       
        # range_name = 'A2:F'  
        # request_body = {
        #     'value_input_option': 'USER_ENTERED',  
        #     'data': [
        #         {
        #             'range': range_name,  
        #             'values': data_to_write,  
        #         }
        #     ]
        # }
        # service = discovery.build('sheets', 'v4', credentials=creds)
        # response = service.spreadsheets().values().batchUpdate(spreadsheetId=sheet.id, body=request_body).execute()

       
        # print(response)
        # print(reason)

