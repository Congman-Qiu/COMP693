DROP SCHEMA IF EXISTS lincolnfitness;

CREATE DATABASE `lincolnfitness`;

USE lincolnfitness;

-- 1 user tables

CREATE TABLE `usertype` (
  `usertypeid` int NOT NULL AUTO_INCREMENT,
  `usertypename` varchar(20) NOT NULL,
  PRIMARY KEY (`usertypeid`)
);

CREATE TABLE `user` (
  `userid` int NOT NULL AUTO_INCREMENT,
  `username` varchar(20) NOT NULL,
  `usertypeid` int NOT NULL,
  `firstname` varchar(45) NOT NULL,
  `familyname` varchar(45) NOT NULL,
  `dateofbirth` date DEFAULT NULL,
  `housenumbername` varchar(15) DEFAULT NULL,
  `street` varchar(20) DEFAULT NULL,
  `town` varchar(25) DEFAULT NULL,
  `city` varchar(25) DEFAULT NULL,
  `postalcode` varchar(4) DEFAULT NULL,
  `isactive` tinyint NOT NULL,
  PRIMARY KEY (`userid`),
  KEY `usertype_idx` (`usertypeid`),
  CONSTRAINT `usertype` FOREIGN KEY (`usertypeid`) REFERENCES `usertype` (`usertypeid`)
);

-- 2 room table

CREATE TABLE `room` (
  `roomid` int NOT NULL AUTO_INCREMENT,
  `roomtype` varchar(45) NOT NULL,
  `roomname` varchar(45) NOT NULL,
  `capacity` int NOT NULL,
  PRIMARY KEY (`roomid`)
);

-- 3 class tables

CREATE TABLE `classmaster` (
  `classmasterid` int NOT NULL AUTO_INCREMENT,
  `classname` varchar(20) NOT NULL,
  `classtype` varchar(20) NOT NULL,
  PRIMARY KEY (`classmasterid`)
);

CREATE TABLE `class` (
  `classid` int NOT NULL AUTO_INCREMENT,
  `classmasterid` int NOT NULL,
  `roomid` int NOT NULL,
  `trainerid` int NOT NULL,
  `fee` int NOT NULL,
  `startdatetime` datetime NOT NULL,
  `enddatetime` datetime NOT NULL,
  PRIMARY KEY (`classid`),
  KEY `classmaster_idx` (`classmasterid`),
  KEY `trainer_idx` (`trainerid`),
  KEY `room_idx` (`roomid`),
  CONSTRAINT `classmaster` FOREIGN KEY (`classmasterid`) REFERENCES `classmaster` (`classmasterid`),
  CONSTRAINT `trainer` FOREIGN KEY (`trainerid`) REFERENCES `user` (`userid`),
  CONSTRAINT `room` FOREIGN KEY (`roomid`) REFERENCES `room` (`roomid`)
);

-- 4 attendance table

CREATE TABLE `attendance` (
  `attendanceid` int NOT NULL AUTO_INCREMENT,
  `classid` int NOT NULL,
  `memberid` int NOT NULL,
  `datetimeattended` DATETIME NULL,
  PRIMARY KEY (`attendanceid`),
  KEY `class_idx` (`classid`),
  KEY `member_idx` (`memberid`),
  CONSTRAINT `class` FOREIGN KEY (`classid`) REFERENCES `class` (`classid`),
  CONSTRAINT `memberx1` FOREIGN KEY (`memberid`) REFERENCES `user` (`userid`)
);

-- 5 enrolment table

CREATE TABLE `enrollment` (
  `enrollmentid` int NOT NULL AUTO_INCREMENT,
  `classid` int NOT NULL,
  `memberid` int NOT NULL,
  `ischeckedin` BIT NULL,
  `paymentid` INT NULL,
  `isactive` INT NULL,
  PRIMARY KEY (`enrollmentid`),
  KEY `class_idx` (`classid`),
  KEY `member_idx` (`memberid`),
  CONSTRAINT `classx1` FOREIGN KEY (`classid`) REFERENCES `class` (`classid`),
  CONSTRAINT `memberx2` FOREIGN KEY (`memberid`) REFERENCES `user` (`userid`)
);

-- 6 news table 

CREATE TABLE news (
	`newsid` INT NOT NULL AUTO_INCREMENT, 
    `title` VARCHAR(500) NOT NULL, 
    `newsdetail` VARCHAR(1000) NOT NULL,
    `newsdate` DATE NOT NULL,
    `authorid` INT NOT NULL,
    `issent` BIT NOT NULL,
    `isactive` BIT NOT NULL,
    PRIMARY KEY (`newsid`),
    FOREIGN KEY (`authorid`) REFERENCES `user`(`userid`)
);

-- 7 payment table 

CREATE TABLE payment (
    `paymentid` INT NOT NULL AUTO_INCREMENT, 
    `userid` INT NOT NULL, 
    `method` VARCHAR(500) NOT NULL, 
    `amount` DECIMAL(10,2) NOT NULL,
    `bankname` VARCHAR(100) NULL,
    `accountnumber` VARCHAR(50) NULL,
    `cardname` VARCHAR(100) NULL,
    `cardnumber` VARCHAR(100) NULL,
    `cardexpirydate` VARCHAR(10) NULL,
    `cardcvv` INT NULL,
    `paymentdate` DATETIME NULL,
    PRIMARY KEY (`paymentid`),
    FOREIGN KEY (`userid`) REFERENCES `user`(`userid`)
);

-- 8 subscription table

CREATE TABLE `subscription` (
  `subscriptionid` int NOT NULL AUTO_INCREMENT,
  `memberid` int NOT NULL,
  `startdate` date NOT NULL,
  `enddate` date NOT NULL,
  `paymentid` int NULL, 
  `isactive` bit NULL,
  PRIMARY KEY (`subscriptionid`),
  KEY `member_idx` (`memberid`),
  CONSTRAINT `member` FOREIGN KEY (`memberid`) REFERENCES `user` (`userid`)
);

-- master data initialisation

INSERT INTO usertype (
    usertypename) VALUES 
(   'admin'),
(   'trainer'),
(   'member');

INSERT INTO user (	
    username,           usertypeid,   firstname,  familyname, dateofbirth,    housenumbername,    street,         town,           city,           postalcode, isactive) VALUES 
(   'demo-admin',       '1',          'Simon',    'Charles',  null,           null,               null,           null,           null,           null,       1),
(   'demo-trainer-1',   '2',          'Ciara',    'Hull',     '1980-07-24',   'Elizabeth Lodge',  'Elmwood Drive','Lincoln',      'Lincoln',      '7608',     1),
(   'demo-trainer-2',   '2',          'Julian',   'Ball',     '1992-06-24',   'Olivia Lodge',     'Tamaki Drive', 'Lincoln',      'Lincoln',      '7608',     1),
(   'demo-member-1',    '3',          'Di',       'Wang',     '2003-05-05',   '2',                'Windsor Place','Hoon Hay',     'Christchurch', '8034',     1),
(   'demo-member-2',    '3',          'Roxanne',  'Acevedo',  '1999-04-04',   '5',                'May Road',     'Prebbleton',   'Prebbleton',   '7601',     1),
(   'demo-member-3',    '3',          'Max',      'Cisneros', '2002-07-25',   '12',               'Kestev Drive', 'Lincoln',      'Lincoln',      '7608',     1);

INSERT INTO room (
    roomtype,       roomname,   capacity) VALUES 
(   'Training Area','Kiwi',     100),
(   'Session Room', 'Warou',    30),
(   'Session Room', 'Tauhou',   30),
(   'Session Room', 'Atawhai',  2);

INSERT INTO classmaster (
    classname,            classtype) VALUES 
(   'Ciara Magic',			  'Specialised Training'),
(   'Spark CrossFit',	    'Exercise Class'),
(   'Serious Work Outs',  'Exercise Class'),
(   'Yoga',				        'Exercise Class'),
(   'Dance',				      'Exercise Class'),
(   'Julian Go',			    'Specialised Training'),
(   'Self Training',		  'Self Training');

INSERT INTO class 
(classmasterid, roomid, 	trainerid, 	fee, 	startdatetime, 			    enddatetime) VALUES
(1 ,	          1,			  2,			    100,	'2023-03-28 14:00:00',	'2023-03-28 15:00:00'),
(2 ,	          2,			  2,			    0,		'2023-03-29 10:00:00',	'2023-03-29 11:00:00'),
(3 ,	          3,			  3,			    0,		'2023-03-30 09:00:00',	'2023-03-30 10:00:00'),
(4 ,	          4,			  3,			    0,		'2023-03-31 11:00:00',	'2023-03-31 12:00:00'),
(5 ,	          4,			  2,			    0,		'2023-04-01 13:00:00',	'2023-04-01 14:00:00'),
(6 ,	          1,			  3,			    100,	'2023-04-02 14:00:00',	'2023-04-02 15:00:00'),
(1 ,	          1,			  2,			    100,	'2023-04-03 14:00:00',	'2023-04-03 15:00:00'),
(2 ,	          2,			  2,			    0,		'2023-04-04 10:00:00',	'2023-04-04 11:00:00'),
(3 ,	          3,			  3,			    0,		'2023-04-05 09:00:00',	'2023-04-05 10:00:00'),
(4 ,	          4,			  3,			    0,		'2023-04-06 11:00:00',	'2023-04-06 12:00:00'),
(5 ,	          4,			  2,			    0,		'2023-04-07 13:00:00',	'2023-04-07 14:00:00'),
(6 ,	          1,			  3,			    100,	'2023-04-08 14:00:00',	'2023-04-08 15:00:00'),
(7 ,	          1,			  1,			    0,		'2018-01-01 00:00:00',	'2099-12-31 23:59:59');