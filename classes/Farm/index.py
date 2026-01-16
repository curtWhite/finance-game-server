from app import db
from app.utils.db_guard import db_call_guard
from classes.Business.index import Business
from bson import ObjectId
from datetime import datetime, timedelta
import random


farm_collection = db["farms-collection"]


# Animal type configurations
ANIMAL_CONFIGS = {
    "cow": {"lifespanMonths": 240, "gestationMonths": 9, "products": ["beef", "milk"]},
    "chicken": {"lifespanMonths": 60, "gestationMonths": 1, "products": ["meat", "eggs"]},
    "goat": {"lifespanMonths": 180, "gestationMonths": 5, "products": ["meat", "milk"]},
    "pig": {"lifespanMonths": 180, "gestationMonths": 4, "products": ["meat", "pork"]},
    "sheep": {"lifespanMonths": 144, "gestationMonths": 5, "products": ["meat", "wool"]},
}

# Seed conversion rates (how many bags of produce = 1 bag of seeds)
SEED_CONVERSION_RATES = {
    "rice": 20,
    "tomato": 10,
    "wheat": 15,
    "corn": 12,
    "potato": 8,
    "soybean": 18,
}

# Crop growth times in game days
CROP_GROWTH_TIMES = {
    "rice": 120,  # ~4 months
    "tomato": 90,  # ~3 months
    "wheat": 100,  # ~3.3 months
    "corn": 110,  # ~3.7 months
    "potato": 80,  # ~2.7 months
    "soybean": 105,  # ~3.5 months
}


class Farm(Business):
    """
    Farm Class - Extends Business
    Specializes in farm-specific functionality like plants/plots management and animal care.
    """
    
    def __init__(self, data=None):
        super().__init__(data)
        self.farmType = "crop"  # 'cattle' or 'crop'
        self.plants = []
        self.animals = []
        self.manager = None
        self.propertyId = None
        self.extraData = {}
        self.type = "farm"
        
        if data:
            self.load(data)
    
    @staticmethod
    def createFarm(name, farmType, numberOfPlots, propertyId=None, username=None, extraData=None):
        """
        Create farm with specified number of plots.
        
        Args:
            name: Farm name
            farmType: 'cattle' or 'crop'
            numberOfPlots: Number of plots to create
            propertyId: Optional property ID where farm is located
            username: Username of the farm owner
            extraData: Extra data for the farm
        
        Returns:
            Farm instance
        """
        plants = []
        for i in range(1, numberOfPlots + 1):
            plants.append({
                "id": f"plot_{int(datetime.utcnow().timestamp() * 1000)}_{i}",
                "plotNumber": i,
                "produceType": None,
                "produceId": None,
                "plantedDate": None,
                "harvestDate": None,
                "status": "idle",
            })
        
        farm = Farm({
            "name": name,
            "farmType": farmType,
            "plants": plants,
            "propertyId": propertyId,
            "username": username,
            "moneyAccount": {
                "balance": 0,
                "logs": [],
            },
            "storage": {
                "items": [],
                "maxCapacity": 5,
            },
            "extraData": extraData or {},
        })
        
        return farm
    
    def plantSeed(self, plotNumber, seedType, fromGlobalStorage=False, globalStorage=None):
        """
        Plant seed on a plot (consumes 1 seed bag).
        
        Args:
            plotNumber: Plot number to plant on
            seedType: Type of seed (e.g., 'rice', 'tomato')
            fromGlobalStorage: Whether to use global storage
            globalStorage: Global storage dictionary (if fromGlobalStorage is True)
        
        Returns:
            bool: True if successful
        """
        plant = next((p for p in self.plants if p.get("plotNumber") == plotNumber), None)
        if not plant:
            return False
        if plant.get("status") != "idle":
            return False  # Can only plant on idle plots
        
        seedBagType = f"{seedType}_seed"
        
        # Check storage for seed bag
        seedFound = False
        if fromGlobalStorage and globalStorage:
            seedItem = next((i for i in globalStorage.get("items", []) if i.get("type") == seedBagType), None)
            if seedItem and seedItem.get("quantity", 0) >= 1:
                seedItem["quantity"] -= 1
                if seedItem["quantity"] <= 0:
                    globalStorage["items"].remove(seedItem)
                seedFound = True
        else:
            # Check farm storage
            seedItem = next((i for i in self.storage["items"] if i.get("type") == seedBagType), None)
            if seedItem and seedItem.get("quantity", 0) >= 1:
                self.removeFromStorage(seedItem["id"], 1)
                seedFound = True
        
        if not seedFound:
            return False
        
        # Get growth time for this crop
        growthDays = CROP_GROWTH_TIMES.get(seedType, 90)  # Default 90 days
        now = datetime.utcnow()
        harvestDate = now + timedelta(days=growthDays)
        
        plant["produceType"] = seedType
        plant["produceId"] = f"produce_{int(now.timestamp() * 1000)}_{plotNumber}"
        plant["plantedDate"] = now.isoformat()
        plant["harvestDate"] = harvestDate.isoformat()
        plant["status"] = "planted"
        
        # Track expense for seed purchase (if applicable)
        self.deductMoney(0, f"Planted {seedType} seeds on plot {plotNumber}", "purchase")
        
        return True
    
    def assignProduceToPlot(self, plotNumber, produceType, produceId):
        """
        Assign produce to a plant/plot (legacy method, use plantSeed instead).
        
        Args:
            plotNumber: Plot number
            produceType: Type of produce
            produceId: Produce ID
        
        Returns:
            bool: True if successful
        """
        plant = next((p for p in self.plants if p.get("plotNumber") == plotNumber), None)
        if not plant:
            return False
        if plant.get("status") != "idle":
            return False  # Can only assign to idle plots
        
        growthDays = CROP_GROWTH_TIMES.get(produceType, 90)
        now = datetime.utcnow()
        harvestDate = now + timedelta(days=growthDays)
        
        plant["produceType"] = produceType
        plant["produceId"] = produceId
        plant["plantedDate"] = now.isoformat()
        plant["harvestDate"] = harvestDate.isoformat()
        plant["status"] = "planted"
        
        return True
    
    def convertProduceToSeeds(self, produceType, quantity):
        """
        Convert produce to seeds (n bags of produce = 1 bag of seeds).
        
        Args:
            produceType: Type of produce
            quantity: Quantity of produce to convert
        
        Returns:
            bool: True if successful
        """
        conversionRate = SEED_CONVERSION_RATES.get(produceType)
        if not conversionRate:
            return False
        
        # Check if we have enough produce
        produceItem = next(
            (i for i in self.storage["items"] 
             if i.get("type") == produceType or i.get("name") == produceType),
            None
        )
        if not produceItem or produceItem.get("quantity", 0) < quantity:
            return False
        
        # Calculate how many seed bags we can make
        seedBagsToCreate = quantity // conversionRate
        if seedBagsToCreate < 1:
            return False
        
        # Remove produce
        produceToRemove = seedBagsToCreate * conversionRate
        self.removeFromStorage(produceItem["id"], produceToRemove)
        
        # Add seed bags
        seedBagType = f"{produceType}_seed"
        existingSeedBag = next((i for i in self.storage["items"] if i.get("type") == seedBagType), None)
        if existingSeedBag:
            existingSeedBag["quantity"] += seedBagsToCreate
        else:
            self.addToStorage({
                "id": f"seed_{int(datetime.utcnow().timestamp() * 1000)}_{random.randint(1000, 9999)}",
                "name": f"{produceType} Seeds",
                "type": seedBagType,
                "quantity": seedBagsToCreate,
                "unit": "bags",
            })
        
        return True
    
    def harvestPlot(self, plotNumber, quantity=None):
        """
        Harvest produce from a plot.
        
        Args:
            plotNumber: Plot number to harvest
            quantity: Quantity to harvest (default: 1)
        
        Returns:
            bool: True if successful
        """
        plant = next((p for p in self.plants if p.get("plotNumber") == plotNumber), None)
        if not plant or not plant.get("produceId") or not plant.get("produceType"):
            return False
        if plant.get("status") != "ready":
            return False
        
        # Default quantity is 1 bag per plot
        harvestQuantity = quantity or 1
        
        # Add harvested produce to farm storage
        success = self.addToStorage({
            "id": f"harvest_{int(datetime.utcnow().timestamp() * 1000)}_{plotNumber}",
            "name": plant["produceType"],
            "type": plant["produceType"],
            "quantity": harvestQuantity,
            "unit": "bags",
        })
        
        if success:
            # Reset plot
            plant["status"] = "idle"
            plant["produceType"] = None
            plant["produceId"] = None
            plant["plantedDate"] = None
            plant["harvestDate"] = None
        
        return success
    
    def updatePlantStatuses(self):
        """Update plant status (call this periodically to update growing -> ready)."""
        now = datetime.utcnow()
        for plant in self.plants:
            status = plant.get("status")
            if status in ["growing", "planted"]:
                harvestDateStr = plant.get("harvestDate")
                if harvestDateStr:
                    try:
                        if isinstance(harvestDateStr, str):
                            harvestDate = datetime.fromisoformat(harvestDateStr.replace('Z', '+00:00'))
                        else:
                            harvestDate = harvestDateStr
                        
                        if now >= harvestDate:
                            plant["status"] = "ready"
                        elif status == "planted":
                            plant["status"] = "growing"
                    except Exception as e:
                        print(f"Error parsing harvest date: {e}")
    
    def getIdlePlots(self):
        """Get all idle plots."""
        return [p for p in self.plants if p.get("status") == "idle"]
    
    def getReadyPlots(self):
        """Get all ready plots (ready for harvest)."""
        return [p for p in self.plants if p.get("status") == "ready"]
    
    def addAnimal(self, animalType, birthDate=None):
        """
        Add animal to farm.
        
        Args:
            animalType: Type of animal (e.g., 'cow', 'chicken')
            birthDate: Optional birth date (default: now)
        
        Returns:
            bool: True if successful
        """
        config = ANIMAL_CONFIGS.get(animalType.lower())
        if not config:
            return False
        
        now = birthDate or datetime.utcnow()
        expirationDate = now + timedelta(days=config["lifespanMonths"] * 30)  # Approximate months to days
        
        animal = {
            "id": f"animal_{int(now.timestamp() * 1000)}_{random.randint(1000, 9999)}",
            "type": animalType.lower(),
            "birthDate": now.isoformat(),
            "expirationDate": expirationDate.isoformat(),
            "isPregnant": False,
            "pregnancyStartDate": None,
            "birthCount": 0,
            "products": config["products"],
            "lastFedDate": None,
            "lastProductCollectionDate": None,
        }
        
        self.animals.append(animal)
        return True
    
    def feedAnimal(self, animalId):
        """
        Feed an animal (required for production).
        
        Args:
            animalId: Animal ID
        
        Returns:
            bool: True if successful
        """
        animal = next((a for a in self.animals if a.get("id") == animalId), None)
        if not animal:
            return False
        
        animal["lastFedDate"] = datetime.utcnow().isoformat()
        return True
    
    def checkPregnancy(self, currentGameDate):
        """
        Check and handle pregnancy logic.
        
        Args:
            currentGameDate: Current game date (datetime)
        """
        for animal in self.animals:
            if animal.get("isPregnant") and animal.get("pregnancyStartDate"):
                config = ANIMAL_CONFIGS.get(animal.get("type"))
                if not config:
                    continue
                
                try:
                    pregnancyStart = datetime.fromisoformat(animal["pregnancyStartDate"].replace('Z', '+00:00'))
                    gestationEndDate = pregnancyStart + timedelta(days=config["gestationMonths"] * 30)
                    
                    if currentGameDate >= gestationEndDate:
                        # Animal gives birth
                        self.processBirth(animal)
                except Exception as e:
                    print(f"Error checking pregnancy: {e}")
            elif not animal.get("isPregnant") and animal.get("birthCount", 0) < 5:
                # Check if animal can get pregnant (base probability 50%, decreases by 10% per birth)
                baseProbability = 0.5
                probability = max(0, baseProbability - (animal.get("birthCount", 0) * 0.1))
                
                if random.random() < probability:
                    animal["isPregnant"] = True
                    animal["pregnancyStartDate"] = currentGameDate.isoformat()
    
    def processBirth(self, animal):
        """Process animal birth."""
        config = ANIMAL_CONFIGS.get(animal.get("type"))
        if not config:
            return
        
        # Create offspring (1-3 offspring per birth)
        offspringCount = random.randint(1, 3)
        for i in range(offspringCount):
            self.addAnimal(animal.get("type"), datetime.utcnow())
        
        # Update parent animal
        animal["isPregnant"] = False
        animal["pregnancyStartDate"] = None
        animal["birthCount"] = animal.get("birthCount", 0) + 1
    
    def checkExpiration(self, currentGameDate):
        """
        Check for expired animals and remove them.
        
        Args:
            currentGameDate: Current game date (datetime)
        
        Returns:
            List of expired animals
        """
        expiredAnimals = []
        remainingAnimals = []
        
        for animal in self.animals:
            try:
                expirationDate = datetime.fromisoformat(animal["expirationDate"].replace('Z', '+00:00'))
                if currentGameDate >= expirationDate:
                    expiredAnimals.append(animal)
                else:
                    remainingAnimals.append(animal)
            except Exception as e:
                print(f"Error checking expiration: {e}")
                remainingAnimals.append(animal)  # Keep if error parsing
        
        self.animals = remainingAnimals
        return expiredAnimals
    
    def collectProducts(self, animalId):
        """
        Collect products from an animal.
        
        Args:
            animalId: Animal ID
        
        Returns:
            List of collected product items
        """
        animal = next((a for a in self.animals if a.get("id") == animalId), None)
        if not animal or not animal.get("lastFedDate"):
            return []  # Animal must be fed to produce
        
        now = datetime.utcnow()
        lastCollectionStr = animal.get("lastProductCollectionDate")
        
        daysSinceLastCollection = 999  # First collection
        if lastCollectionStr:
            try:
                lastCollection = datetime.fromisoformat(lastCollectionStr.replace('Z', '+00:00'))
                daysSinceLastCollection = (now - lastCollection).days
            except:
                pass
        
        # Products can be collected daily
        if daysSinceLastCollection < 1:
            return []  # Already collected today
        
        collectedProducts = []
        for productType in animal.get("products", []):
            # Generate random quantity based on product type
            quantity = 1
            if productType in ["milk", "eggs"]:
                quantity = random.randint(1, 5)  # 1-5 units
            elif productType == "wool":
                quantity = random.randint(1, 3)  # 1-3 units
            
            productItem = {
                "id": f"{productType}_{int(now.timestamp() * 1000)}_{random.randint(1000, 9999)}",
                "name": productType,
                "type": productType,
                "quantity": quantity,
                "unit": "units",
                "addedDate": now.isoformat(),
            }
            
            self.addToStorage(productItem)
            collectedProducts.append(productItem)
        
        animal["lastProductCollectionDate"] = now.isoformat()
        return collectedProducts
    
    def getAnimal(self, animalId):
        """Get animal by ID."""
        return next((a for a in self.animals if a.get("id") == animalId), None)
    
    def getAnimalsNeedingFeed(self):
        """Get all animals that need feeding."""
        now = datetime.utcnow()
        animalsNeedingFeed = []
        
        for animal in self.animals:
            lastFedStr = animal.get("lastFedDate")
            if not lastFedStr:
                animalsNeedingFeed.append(animal)
                continue
            
            try:
                lastFed = datetime.fromisoformat(lastFedStr.replace('Z', '+00:00'))
                daysSinceFed = (now - lastFed).days
                if daysSinceFed >= 1:  # Need feeding daily
                    animalsNeedingFeed.append(animal)
            except:
                animalsNeedingFeed.append(animal)  # If error parsing, assume needs feed
        
        return animalsNeedingFeed
    
    def transferToGlobalStorage(self, itemId, quantity, globalStorage):
        """
        Transfer items from farm storage to global storage.
        
        Args:
            itemId: Item ID to transfer
            quantity: Quantity to transfer
            globalStorage: Global storage dictionary
        
        Returns:
            bool: True if successful
        """
        item = next((i for i in self.storage["items"] if i.get("id") == itemId), None)
        if not item or item.get("quantity", 0) < quantity:
            return False
        
        # Remove from farm storage
        self.removeFromStorage(itemId, quantity)
        
        # Add to global storage
        existingItem = next(
            (i for i in globalStorage.get("items", []) 
             if i.get("id") == itemId or (i.get("type") == item.get("type") and i.get("name") == item.get("name"))),
            None
        )
        if existingItem:
            existingItem["quantity"] += quantity
        else:
            globalStorage.setdefault("items", []).append({
                **item,
                "quantity": quantity,
                "addedDate": datetime.utcnow().isoformat(),
            })
        
        return True
    
    def transferFromGlobalStorage(self, itemId, quantity, globalStorage):
        """
        Transfer items from global storage to farm storage.
        
        Args:
            itemId: Item ID to transfer
            quantity: Quantity to transfer
            globalStorage: Global storage dictionary
        
        Returns:
            bool: True if successful
        """
        item = next((i for i in globalStorage.get("items", []) if i.get("id") == itemId), None)
        if not item or item.get("quantity", 0) < quantity:
            return False
        
        # Remove from global storage
        item["quantity"] -= quantity
        if item["quantity"] <= 0:
            globalStorage["items"].remove(item)
        
        # Add to farm storage
        self.addToStorage({
            "id": item["id"],
            "name": item["name"],
            "type": item["type"],
            "quantity": quantity,
            "unit": item.get("unit", "units"),
        })
        
        return True
    
    def hireManager(self, manager):
        """
        Hire a manager.
        
        Args:
            manager: Dictionary with id, name, salary, automationLevel
        
        Returns:
            bool: True if successful
        """
        if self.manager:
            return False  # Already has a manager
        
        self.manager = {
            **manager,
            "hiredDate": datetime.utcnow().isoformat(),
        }
        
        # Deduct first month's salary
        self.deductMoney(manager.get("salary", 0), f"Manager salary: {manager.get('name', '')}", "purchase")
        return True
    
    def fireManager(self):
        """Fire the current manager."""
        if not self.manager:
            return False
        self.manager = None
        return True
    
    def updateTimers(self, currentGameDate):
        """
        Update all timers (crops, animals, pregnancy).
        
        Args:
            currentGameDate: Current game date (datetime)
        """
        # Update plant statuses
        self.updatePlantStatuses()
        
        # Check animal pregnancies
        self.checkPregnancy(currentGameDate)
        
        # Check animal expiration
        expiredAnimals = self.checkExpiration(currentGameDate)
        if expiredAnimals:
            # Expired animals can be harvested for final products
            for animal in expiredAnimals:
                for productType in animal.get("products", []):
                    self.addToStorage({
                        "id": f"{productType}_expired_{int(datetime.utcnow().timestamp() * 1000)}",
                        "name": productType,
                        "type": productType,
                        "quantity": 1,
                        "unit": "units",
                    })
    
    def toDict(self):
        """Convert to dictionary including farm-specific fields."""
        base = super().toDict()
        return {
            **base,
            "farmType": self.farmType,
            "plants": self.plants,
            "animals": self.animals,
            "manager": self.manager,
            "propertyId": self.propertyId,
            "extraData": self.extraData,
        }
    
    def load(self, data):
        """Load from dictionary including farm-specific fields."""
        super().load(data)
        self.farmType = data.get("farmType", "crop")
        self.propertyId = data.get("propertyId")
        self.plants = data.get("plants", [])
        self.animals = data.get("animals", [])
        self.manager = data.get("manager")
        self.extraData = data.get("extraData", {})
        self.type = "farm"
    
    def save_to_db(self):
        """Save the current farm state to the database."""
        try:
            with db_call_guard("Farm.save_to_db"):
                data = self.toDict()
                # Remove id from data for MongoDB operations
                farm_id = data.pop("id", None)
                
                if farm_id:
                    _id = farm_id
                    if _id and not isinstance(_id, ObjectId):
                        try:
                            _id = ObjectId(_id)
                        except:
                            pass
                    
                    result = farm_collection.update_one(
                        {"_id": _id},
                        {"$set": data}
                    )
                    if result.modified_count == 0 and result.matched_count == 0:
                        # If not found, insert as new
                        data["_id"] = _id
                        farm_collection.insert_one(data)
                else:
                    # Insert new document
                    result = farm_collection.insert_one(data)
                    self._id = result.inserted_id
        except Exception as e:
            print(f"Exception occurred in Farm.save_to_db: {e}")
            raise
    
    @classmethod
    def load_from_db(cls, farm_id=None, username=None, name=None):
        """
        Load farm from database.
        
        Args:
            farm_id: MongoDB _id of the farm
            username: Username of the farm owner
            name: Name of the farm
        
        Returns:
            Farm instance or None if not found
        """
        try:
            with db_call_guard("Farm.load_from_db"):
                query = {}
                if farm_id:
                    if not isinstance(farm_id, ObjectId):
                        try:
                            farm_id = ObjectId(farm_id)
                        except:
                            return None
                    query["_id"] = farm_id
                elif username and name:
                    query["username"] = username
                    query["name"] = name
                elif username:
                    query["username"] = username
                else:
                    return None
                
                doc = farm_collection.find_one(query)
                if doc:
                    instance = cls()
                    instance.load(doc)
                    instance._id = doc.get("_id")
                    instance.username = username
                    return instance
        except Exception as e:
            print(f"Exception occurred in Farm.load_from_db: {e}")
        return None
    
    @classmethod
    def load_all_by_username(cls, username):
        """
        Load all farms for a username.
        
        Args:
            username: Username of the farm owner
        
        Returns:
            List of Farm instances
        """
        try:
            with db_call_guard("Farm.load_all_by_username"):
                cursor = farm_collection.find({"username": username})
                farms = []
                for doc in cursor:
                    instance = cls()
                    instance.load(doc)
                    instance._id = doc.get("_id")
                    farms.append(instance)
                return farms
        except Exception as e:
            print(f"Exception occurred in Farm.load_all_by_username: {e}")
            return []
