from flask import Flask, render_template, request, jsonify
from flask_cors import CORS, cross_origin
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import pymongo
import logging
logging.basicConfig(filename="scrapper.log", level=logging.INFO)

application = Flask(__name__) 
app = application


@app.route('/', methods=['GET'])  
@cross_origin()
def homePage():
    return render_template("index.html")

@app.route('/review', methods=['POST', 'GET']) 
@cross_origin()
def index():
    if request.method == 'POST':
        try:
            searchString = request.form['content'].strip()
            if not searchString:
                return render_template('index.html', error="Please enter a search term")
            searchStringFormatted = searchString.replace(" ", "")
            flipkart_url = "https://www.flipkart.com/search?q=" + searchStringFormatted
            logging.info(f"Fetching data for: {searchString}")
            
            # Fetch product listings
            uClient = uReq(flipkart_url)
            flipkartPage = uClient.read()
            uClient.close()
            flipkart_html = bs(flipkartPage, "html.parser")
            bigboxes = flipkart_html.findAll("div", {"class": "cPHDOP col-12-12"})
            
            if not bigboxes or len(bigboxes) < 4:
                return render_template('index.html', error="No products found. Please try a different search term.")
                
            del bigboxes[0:3]
            box = bigboxes[0]
            productLink = "https://www.flipkart.com" + box.div.div.div.a['href']
            
            # Fetch product details
            prodRes = requests.get(productLink)
            prodRes.encoding = 'utf-8'
            prod_html = bs(prodRes.text, "html.parser")
            commentboxes = prod_html.find_all('div', {'class': "RcXBOT"})
            
            if not commentboxes:
                return render_template('index.html', error="No reviews found for this product")
            
            # Process reviews
            reviews = []
            for commentbox in commentboxes:
                try:
                    name = commentbox.div.div.find_all('p', {'class': '_2NsDsF AwS1CA'})[0].text
                except:
                    name = 'Anonymous'
                    
                try:
                    rating = commentbox.div.div.div.div.text
                    rating = f"{rating} ★"  
                except:
                    rating = 'Not Rated'
                    
                try:
                    commentHead = commentbox.div.div.div.p.text
                except:
                    commentHead = 'No Title'
                    
                try:
                    comtag = commentbox.find_all('div', {'class': ''})
                    custComment = comtag[0].div.text if comtag and comtag[0].div else 'No detailed review'
                except Exception as e:
                    custComment = 'No detailed review'
                    logging.error(f"Error processing comment: {e}")

                mydict = {
                    "Product": searchString,
                    "Name": name,
                    "Rating": rating,
                    "CommentHead": commentHead,
                    "Comment": custComment
                }
                reviews.append(mydict)
            
            # Save to MongoDB
            try:
                client = pymongo.MongoClient("mongodb+srv://mohitagarwalq:N495PW544Ca5isPT@cluster0.kgmzehs.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
                db = client['review_scrap']
                review_col = db['review_scrap_data']
                review_col.insert_many(reviews)
                logging.info(f"Successfully saved {len(reviews)} reviews to MongoDB")
            except Exception as e:
                logging.error(f"Error saving to MongoDB: {e}")
            return render_template('results.html', reviews=reviews, product=searchString,count=len(reviews))
                                 
        except Exception as e:
            logging.error(f"Error in processing: {e}")
            return render_template('error.html', error=str(e))
            
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000, debug=True)

































