import requests, re, json, pymongo, time, random
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from faker import Faker

# W=87
# E=69

class LaCentrale(object):
	"""docstring for LaCentrale"""
	def __init__(self):
		super(LaCentrale, self).__init__()
		self.base = "https://www.lacentrale.fr/"
		self.url = "https://www.lacentrale.fr/listing"
		self.argus = "https://www.lacentrale.fr/lacote_origine.php"
		self.webhook = "https://discordapp.com/api/webhooks/"
		self.s = requests.session()
		self.fake = Faker(["fr_FR"])
		self.myclient = pymongo.MongoClient("mongodb://localhost:27017/")
		self.headers = {
			'authority': 'www.lacentrale.fr',
			'upgrade-insecure-requests': '1',
			'user-agent': self.fake.user_agent(),
			'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
			'sec-fetch-site': 'none',
			'sec-fetch-mode': 'navigate',
			'sec-fetch-user': '?1',
			'sec-fetch-dest': 'document',
			'accept-language': 'en,en-US;q=0.9,fr;q=0.8',
		}
		self.page = 1
		self.geolocator = Nominatim(user_agent=self.fake.user_agent())
		

	def getParams(self):
		params = {
			'age': '7',
			'autoviza': 'true',
			'goodDealBadges': 'VERY_GOOD_DEAL',
		}
		if(self.page!=1):
			params['page'] = self.page
		return params

	def parseHtml(self,r):
		soup = BeautifulSoup(r.text, 'html.parser')
		scripts = soup.findAll('script')
		script = None
		for i in scripts:
			if("__PRELOADED_STATE__" in i.text):
				script = i.text
		return script

	def getVehicles(self,js):
		vehicles = []
		results = js["search"]["hits"]
		for car in results:
			if(car["item"]["vehicle"]["family"] != "AUTO"):
				continue
			vehicle = car["item"]["vehicle"]
			vehicle["reference"] = car["item"]["reference"]
			vehicle["customerType"] = car["item"]["customerType"]
			vehicle["price"] = car["item"]["price"]
			vehicle["location"] = car["item"]["location"]
			vehicle["date"] = car["item"]["firstOnlineDate"]
			vehicle["photoUrl"] = car["item"]["photoUrl"]
			vehicle["deal"] = car["item"]["goodDealBadge"]
			vehicle["photoUrl"] = car["item"]["photoUrl"]
			if(vehicle["reference"][:1] == "W"):
				link = "87"+vehicle["reference"][1:]
			elif(vehicle["reference"][:1] == "E"):
				link = "69"+vehicle["reference"][1:]
			elif(vehicle["reference"][:1] == "B"):
				link = "66"+vehicle["reference"][1:]
			else:
				print("\n--------------")
				print("Error while trying to get product link")
				print(vehicle)
				print("--------------\n")
				break;
			vehicle["link"] = 'https://www.lacentrale.fr/auto-occasion-annonce-'+link+'.html'
			vehicles.append(vehicle)
		return vehicles

	def retrieveJSON(self,text):	
		regex = r"_STATE__ = (.*)"
		matches = re.finditer(regex, text, re.MULTILINE)
		for matchNum, match in enumerate(matches, start=1):
			print ("Match {matchNum} was found at {start}-{end}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
			for groupNum in range(0, len(match.groups())):
				groupNum = groupNum + 1
				print ("Group {groupNum} found at {start}-{end}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))
				js = json.loads(match.group(groupNum))
		return js

	def existsInMongo(self,vehicle):
		mydb = self.myclient["cars"]
		mycol = mydb["car"]
		query = {"reference":vehicle["reference"]}
		if(mycol.count_documents(query) != 0):
			return True
		else:
			return False

	def postToMongo(self,vehicle):
		mydb = self.myclient["cars"]
		mycol = mydb["car"]
		query = {"reference":vehicle["reference"]}
		if(mycol.count_documents(query) == 0):
			# insert to mycol
			try:
				x = mycol.insert_one(vehicle)
				print("Successfully inserted "+vehicle["reference"]+" - "+vehicle["commercialName"]+" into DB with id: ")
				print(x.inserted_id)
				return True
			except Exception as e:
				print(e)
				return False
		else:
			print("Already in database")
			return False

	def toDiscord(self,vehicle):
		data = {
			"content": "🚨 **NOUVEAU VEHICULE**", 
			"embeds": [
				{
					"title": vehicle["make"]+" "+vehicle["commercialName"], 
					"url": vehicle["link"],
					"thumbnail": {
						"url": vehicle["photoUrl"]
					},
					"description": vehicle["version"],
					"footer": {
						"text": vehicle["details"]["energy"]+" | "+str(vehicle["details"]["power"])+" CH - "+str(vehicle["details"]["cv"])+" CV | "+str(vehicle["details"]["options"])+" options | First hand: "+str(vehicle["details"]["firstHand"]),
					},
					"fields":[
						{
							"name": "ANNEE",
							"value": str(vehicle["year"]),
							"inline": True
						},
						{
							"name": "PRIX 💵",
							"value": str(vehicle["price"])+" €",
							"inline": True
						},
						{
							"name": "KM",
							"value": vehicle["mileage"],
							"inline": True
						},
						{
							"name": "LOCATION 📍",
							"value": self.geolocator.reverse(str(vehicle["location"]["geopoints"]["lat"])+", "+str(vehicle["location"]["geopoints"]["lon"])).address,
							"inline": True
						},
						{
							"name": "ARGUS 📈",
							"value": "Prix vente: ~~"+str(vehicle["price"])+"~~"+"\n"+"Cote brute: "+str(vehicle["argus"]["cote_brute"])+"\n"+"Cote perso: "+str(vehicle["argus"]["cote_perso"]),
							#{"cote_brute":18478,"cote_perso":17020,"year_mileage":12639,"price_new":24200,"indice":{"brute":5,"perso":5},"average_mileage":9479,"commercialModel":"CAPTUR"}
							"inline": True
						},
						{
							"name": "INDICE 🤝",
							"value": "Indice: "+str(vehicle["argus"]["indice"]["brute"])+"\n"+"Indice perso: "+str(vehicle["argus"]["indice"]["perso"]),
							#{"cote_brute":18478,"cote_perso":17020,"year_mileage":12639,"price_new":24200,"indice":{"brute":5,"perso":5},"average_mileage":9479,"commercialModel":"CAPTUR"}
							"inline": True
						},
						{
							"name": "CARADISIAC 💯",
							"value": str(vehicle["caradisiac"]["note"])+"/20\n[Detail]("+str(vehicle["caradisiac"]["noteLink"])+")",
							"inline": True
						},
						{
							"name": "PRIX NEUF 🚙",
							"value": str(vehicle["argus"]["price_new"])+" €",
							"inline": True
						},
						{
							"name": "BILAN FINANCIER",
							"value": str( int( ( (vehicle["price"]-vehicle["argus"]["price_new"]) / vehicle["argus"]["price_new"] ) *100) )+"%  du prix de base\n"+str( int( ( (vehicle["price"]-vehicle["argus"]["cote_perso"]) / vehicle["argus"]["cote_perso"] ) *100) )+"%  du prix cote perso",
							"inline": True
						}
					]
				}
			]
		}
		r = self.s.post(self.webhook,data=json.dumps(data),headers={"Content-Type": "application/json"})
		if(r.status_code != 200):
			print(r.status_code)
			print(r.text)
			return False
		else:
			print("Successfully posted "+vehicle["reference"]+" - "+vehicle["commercialName"]+" to Discord")
			return True

	def getArgusLink(self,vehicle):
		argus = None
		data = {
			'make': vehicle["make"],
			'model': vehicle["model"],
			'year': vehicle["year"]
		}
		r = self.s.post(self.argus,headers=self.headers,data=data)
		try:
			r.raise_for_status()
		except Exception as e:
			print("Error while making request to get argus link")
			print(e)
			return False
		soup = BeautifulSoup(r.text, 'html.parser')
		results = soup.findAll('div',{'class':'listingResultLine'})
		for i in results:
			#print(vehicle["version"] +" - "+ i.findChild().findChild().text.strip().replace(";",""))
			if(vehicle["version"] == i.findChild().findChild().text.strip().replace(";","")):
				argus = i.findChild()['href']
				#print("Found argus: "+argus)
		return self.base+argus

	# mostly getting caradisiac rating, because the other informations will be fetched from another link
	def getRating(self,vehicle,link):
		print(link)
		r = self.s.get(link,headers=self.headers)
		try:
			r.raise_for_status()
		except Exception as e:
			print("Error while making request to get argus")
			print(e)
			return False
		soup = BeautifulSoup(r.text, 'html.parser')
		try:
			vehicle["caradisiac"] = {}
			noteText = soup.find('span',{'class':'noteAvis'})
			vehicle["caradisiac"]["note"] = noteText.findChild().text
			vehicle["caradisiac"]["noteLink"] = noteText.parent.get("href")
		except Exception as e:
			print("Error while trying to get the note")
			print(e)
		try:
			brut1 = soup.find('span',{'class':'jsRefinedQuotBrute'}).text
		except Exception as e:
			print("Error while trying to get the brut1")
			print(e)
		"""
		try:
			indiceClass = soup.find('span',{'class':'graph'})['class']
			indice = re.findall('(\d)',indiceClass)[0]
		except Exception as e:
			print("Error while trying to get the indice")
			print(e)
		"""
		return vehicle
	
	def getArgusJSON(self,vehicle,referer):
		r = self.s.get(referer,headers=self.headers)
		heads = self.headers
		heads["referer"] = referer
		heads['sec-fetch-site'] = 'same-origin'
		heads['sec-fetch-mode'] = 'cors'
		heads['sec-fetch-dest'] = 'empty'
		params = {
			'km': vehicle["mileage"],
			'zipcode': '75001',
			'month': '01',
			'year': vehicle["year"],
			'vertical': 'auto',
		}
		r = self.s.get('https://www.lacentrale.fr/get_co_prox.php', headers=heads, params=params)
		#{"cote_brute":18478,"cote_perso":17020,"year_mileage":12639,"price_new":24200,"indice":{"brute":5,"perso":5},"average_mileage":9479,"commercialModel":"CAPTUR"}
		brut1 = r.json()["cote_brute"]
		brut2 = r.json()["cote_perso"]
		priceNew = r.json()["price_new"]
		indice1 = r.json()["indice"]["brute"]
		indice2 = r.json()["indice"]["perso"]
		return r.json()

	def extractDetails(self,vehicle):
		r = self.s.get(vehicle["link"],headers=self.headers)
		soup = BeautifulSoup(r.text, 'html.parser')
		for i in soup.findAll("script"):
			if("fragment_tracking_state" in i.text):
				script = i.text
		regex = r"fragment_tracking_state = (.*);"
		matches = re.findall(regex,script)
		js = json.loads(matches[0])
		vehicle["details"] = {}
		vehicle["details"]["energy"] = js["vehicle"]["energy"]
		vehicle["details"]["options"] = len(js["vehicle"]["options"])
		vehicle["details"]["firstHand"] = js["vehicle"]["firstHand"]
		vehicle["details"]["power"] = js["vehicle"]["powerDIN"]
		vehicle["details"]["cv"] = js["vehicle"]["ratedHorsePower"]
		return vehicle

	def makeRequest(self):
		params = self.getParams()
		r = self.s.get(self.url,headers=self.headers,params=params)
		if(r.status_code != 200):
			return {"success":False,"response":r}
		else:
			return {"success":True,"response":r}

	def main(self):
		result = self.makeRequest()
		if(result["success"] == False):
			print("Error while scraping LaCentrale")
			print(result["response"].status_code)
			print(result["response"].text)
			# message to discord ALERT
			return False
		script = self.parseHtml(result["response"])
		if(script != None):
			js = self.retrieveJSON(script)
			print(js["search"]["pageSize"])
			print(js["search"]["total"])
			vehicles = self.getVehicles(js) # convert JSON to readable vehicles objects
		else:
			print("Can't retrieve data")
			return False

		while self.page < js["search"]["pageSize"]:
			print("Page "+str(self.page)+" of "+str(js["search"]["pageSize"]))
			result = self.makeRequest()
			self.page += 1
			if(result["success"] == False):
				return False
			script = self.parseHtml(result["response"])
			if(script != None):
				js = self.retrieveJSON(script)
				vehicles = self.getVehicles(js) # convert JSON to readable vehicles objects
			else:
				print("Can't retrieve data on page "+str(self.page))
				return False
			for i in vehicles:
				if(self.existsInMongo(i)):
					print("Already in database")
					continue
				try:
					link = self.getArgusLink(i)
					vehicle = self.getRating(i,link)
					argus = self.getArgusJSON(i,link)
					vehicle = self.extractDetails(i)
					i["argus"] = argus
				except Exception as e:
					print("Error while scraping "+i["reference"]+" - "+i["commercialName"]+" ARGUS")
					print(e)
				try:
					posted = self.postToMongo(i) 
				except Exception as e:
					print("Error while posting "+i["reference"]+" - "+i["commercialName"]+" to Mongo")
					print(e)
					continue
				try:
					if(posted==True): # if posted == true
						self.toDiscord(i)
				except Exception as e:
					print("Error while posting "+i["reference"]+" - "+i["commercialName"]+" to Discord")
					print(e)
					continue
			#time.sleep(random.uniform(1,3))
			


lc = LaCentrale()
lc.main()


#cote argus
#moyenne caradisiac
#= indice confiance


