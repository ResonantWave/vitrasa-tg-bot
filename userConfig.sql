CREATE TABLE `userConfig` (
  `tg_id` varchar(15) NOT NULL,
  `fav0` varchar(50) DEFAULT NULL,
  `fav1` varchar(50) DEFAULT NULL,
  `fav2` varchar(50) DEFAULT NULL,
  `fav3` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`tg_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;