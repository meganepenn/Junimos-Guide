USE stardew;

CREATE TABLE ROOM (
	room_id INT PRIMARY KEY,
    name VARCHAR(255),
    description TEXT, 
    required_bundles INT
);

CREATE TABLE BUNDLE (
	bundle_id INT PRIMARY KEY,
    name VARCHAR(255),
    reward VARCHAR(255),
    seasonal BOOLEAN,
    required_item_count INT,
    room_id INT,
    FOREIGN KEY (room_id) REFERENCES ROOM(room_id)
);

CREATE TABLE ITEM (
	item_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    type VARCHAR(100),
    season VARCHAR(50),
    source VARCHAR(255),
    used_in TEXT,
);

CREATE TABLE BUNDLE_ITEMS (
	bundle_id INT,
    item_name INT,
    quantity_required INT,
    PRIMARY KEY (bundle_id, item_id),
    FOREIGN KEY (bundle_id) REFERENCES BUNDLE(bundle_id),
    FOREIGN KEY (item_id) REFERENCES ITEM(item_id)
);

CREATE TABLE USER (
	user_id INT PRIMARY KEY,
    username VARCHAR(255),
    farm_name VARCHAR(255),
    goal_perfection BOOLEAN,
    love_interest VARCHAR(255)
);

CREATE TABLE USER_BUNDLE_PROGRESS (
	user_id INT,
    bundle_id INT, 
    is_completed BOOLEAN,
    completion_date DATE,
    PRIMARY KEY (user_id, bundle_id),
    FOREIGN KEY (user_id) REFERENCES USER(user_id),
    FOREIGN KEY (bundle_id) REFERENCES BUNDLE(bundle_id)
);

CREATE TABLE USER_CC_PROGRESS (
	user_id INT,
    total_bundles INT,
    bundles_completed INT,
    percent_completed FLOAT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES USER(user_id)
);

CREATE TABLE VILLAGER (
    villager_name VARCHAR(255) PRIMARY KEY,
    birthday_season VARCHAR(50),
    birthdate INT,
    location VARCHAR(250),
    address VARCHAR(250),
    family VARCHAR(500),
    can_marry BOOLEAN
);

CREATE TABLE CHARACTER_GIFT_PREFS (
	villager_name VARCHAR(255), 
    item_id INT,
    preference ENUM('love', 'like', 'neutral', 'dislike', 'hate'),
    PRIMARY KEY (villager_name, item_id),
    FOREIGN KEY (villager_name) REFERENCES VILLAGER(villager_name),
    FOREIGN KEY (item_id) REFERENCES ITEM(item_id)
);

CREATE TABLE USER_CHARACTER_RELATIONSHIP (
	user_id INT,
    villager_name VARCHAR(255),
    heart_level INT DEFAULT 0,
    is_dating BOOLEAN DEFAULT FALSE,
    is_married BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, villager_name),
    FOREIGN KEY (user_id) REFERENCES USER(user_id),
    FOREIGN KEY (villager_name) REFERENCES VILLAGER(villager_name)
);

CREATE TABLE USER_GIFT_HISTORY (
	user_id INT,
    villager_name VARCHAR(255),
    item_id INT,
    gift_date VARCHAR(50),
    PRIMARY KEY (user_id, villager_name, gift_date, item_id),
    FOREIGN KEY (user_id) REFERENCES USER(user_id),
    FOREIGN KEY (villager_name) REFERENCES VILLAGER(villager_name),
    FOREIGN KEY (item_id) REFERENCES ITEM(item_id)
);

CREATE TABLE CHARACTER_EVENTS (
	event_id INT PRIMARY KEY,
    villager_name VARCHAR(255),
    heart_requirement INT,
    event_description TEXT,
    FOREIGN KEY (villager_name) REFERENCES VILLAGER(villager_name)
);

SELECT * FROM ITEM;

UPDATE ITEM
SET type = 'fish';

SELECT * FROM VILLAGER;