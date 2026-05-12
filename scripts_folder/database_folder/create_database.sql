CREATE DATABASE IF NOT EXISTS `rev_acc_database`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

USE `rev_acc_database`;

-- ------------------------------------------------------------
-- Reference tables
-- ------------------------------------------------------------

DROP TABLE IF EXISTS `brand`;
CREATE TABLE `brand` (
    `id_brand`   INT NOT NULL AUTO_INCREMENT,
    `brand_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_brand`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `category`;
CREATE TABLE `category` (
    `id_category`   INT NOT NULL AUTO_INCREMENT,
    `category_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_category`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `distributor`;
CREATE TABLE `distributor` (
    `id_distributor`   INT NOT NULL AUTO_INCREMENT,
    `distributor_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_distributor`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `industrial`;
CREATE TABLE `industrial` (
    `id_industrial`   INT NOT NULL AUTO_INCREMENT,
    `industrial_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_industrial`)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Product
-- ------------------------------------------------------------

DROP TABLE IF EXISTS `product`;
CREATE TABLE `product` (
    `id_product`     INT NOT NULL AUTO_INCREMENT,
    `fk_id_brand`    INT NOT NULL,
    `fk_id_category` INT NOT NULL,
    `product_name`   VARCHAR(255) NOT NULL,
    `description`    TEXT,
    `unit`           VARCHAR(50) NOT NULL,
    PRIMARY KEY (`id_product`),
    FOREIGN KEY (`fk_id_brand`)
        REFERENCES `brand`(`id_brand`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_category`)
        REFERENCES `category`(`id_category`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Agreement
-- ------------------------------------------------------------

DROP TABLE IF EXISTS `agreement`;
CREATE TABLE `agreement` (
    `id_agreement`      INT NOT NULL AUTO_INCREMENT,
    `fk_id_brand`       INT NOT NULL,
    `fk_id_category`    INT NOT NULL,
    `fk_id_distributor` INT NOT NULL,
    `fk_id_industrial`  INT NOT NULL,
    `start_date`        DATE NULL,
    `end_date`          DATE NULL,
    PRIMARY KEY (`id_agreement`),
    FOREIGN KEY (`fk_id_brand`)
        REFERENCES `brand`(`id_brand`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_category`)
        REFERENCES `category`(`id_category`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_distributor`)
        REFERENCES `distributor`(`id_distributor`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_industrial`)
        REFERENCES `industrial`(`id_industrial`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Agreement Tier
-- ------------------------------------------------------------

DROP TABLE IF EXISTS `agreement_tier`;
CREATE TABLE `agreement_tier` (
    `id_agreement_tier` INT   NOT NULL AUTO_INCREMENT,
    `fk_id_agreement`   INT   NOT NULL,
    `min_uvc`           INT   NOT NULL,
    `max_uvc`           INT   DEFAULT NULL,
    `price`             FLOAT NOT NULL,
    PRIMARY KEY (`id_agreement_tier`),
    FOREIGN KEY (`fk_id_agreement`)
        REFERENCES `agreement`(`id_agreement`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Transaction
-- ------------------------------------------------------------

DROP TABLE IF EXISTS `transaction`;
CREATE TABLE `transaction` (
    `id_transaction`    INT NOT NULL AUTO_INCREMENT,
    `fk_id_product`     INT NOT NULL,
    `fk_id_agreement`   INT NOT NULL,
    `fk_id_distributor` INT NOT NULL,
    `quantity`          INT NOT NULL,
    `unit_price`        FLOAT NOT NULL, -- unit price at the time of transaction
    `total_price`       FLOAT NOT NULL,
    `transaction_date`  DATE NOT NULL,
    PRIMARY KEY (`id_transaction`),
    FOREIGN KEY (`fk_id_product`)
        REFERENCES `product`(`id_product`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_agreement`)
        REFERENCES `agreement`(`id_agreement`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_distributor`)
        REFERENCES `distributor`(`id_distributor`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;
