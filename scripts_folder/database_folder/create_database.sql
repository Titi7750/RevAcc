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

DROP TABLE IF EXISTS `unit`;
CREATE TABLE `unit` (
    `id_unit`   INT NOT NULL AUTO_INCREMENT,
    `unit_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_unit`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `data_source`;
CREATE TABLE `data_source` (
    `id_data_source`   INT NOT NULL AUTO_INCREMENT,
    `data_source_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_data_source`)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Product
-- ------------------------------------------------------------

DROP TABLE IF EXISTS `product`;
CREATE TABLE `product` (
    `id_product`     INT NOT NULL AUTO_INCREMENT,
    `fk_id_brand`    INT NOT NULL,
    `fk_id_category` INT NOT NULL,
    `fk_id_unit`     INT NOT NULL,
    `fk_id_data_source` INT NOT NULL,
    `product_name`   VARCHAR(255) NULL,
    `product_code`   VARCHAR(255) NULL,
    `description`    TEXT NULL,
    PRIMARY KEY (`id_product`),
    FOREIGN KEY (`fk_id_brand`)
        REFERENCES `brand`(`id_brand`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_category`)
        REFERENCES `category`(`id_category`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_unit`)
        REFERENCES `unit`(`id_unit`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_data_source`)
        REFERENCES `data_source`(`id_data_source`)
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
    `fk_id_industrial`  INT NOT NULL,
    `fk_id_unit`        INT NOT NULL,
    `start_date`        DATE NULL,
    `end_date`          DATE NULL,
    PRIMARY KEY (`id_agreement`),
    FOREIGN KEY (`fk_id_brand`)
        REFERENCES `brand`(`id_brand`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_category`)
        REFERENCES `category`(`id_category`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_industrial`)
        REFERENCES `industrial`(`id_industrial`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_unit`)
        REFERENCES `unit`(`id_unit`)
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
    `price`             DECIMAL(10, 2) NOT NULL,
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
    `unit_price`        DECIMAL(10, 2) NOT NULL, -- unit price at the time of transaction
    `total_price`       DECIMAL(10, 2) NOT NULL,
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
