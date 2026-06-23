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
    PRIMARY KEY (`id_brand`),
    UNIQUE KEY `uq_brand_name` (`brand_name`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `category`;
CREATE TABLE `category` (
    `id_category`   INT NOT NULL AUTO_INCREMENT,
    `category_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_category`),
    UNIQUE KEY `uq_category_name` (`category_name`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `distributor`;
CREATE TABLE `distributor` (
    `id_distributor`   INT NOT NULL AUTO_INCREMENT,
    `distributor_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_distributor`),
    UNIQUE KEY `uq_distributor_name` (`distributor_name`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `industrial`;
CREATE TABLE `industrial` (
    `id_industrial`   INT NOT NULL AUTO_INCREMENT,
    `industrial_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_industrial`),
    UNIQUE KEY `uq_industrial_name` (`industrial_name`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `unit`;
CREATE TABLE `unit` (
    `id_unit`   INT NOT NULL AUTO_INCREMENT,
    `unit_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_unit`),
    UNIQUE KEY `uq_unit_name` (`unit_name`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS `data_source`;
CREATE TABLE `data_source` (
    `id_data_source`   INT NOT NULL AUTO_INCREMENT,
    `data_source_name` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id_data_source`),
    UNIQUE KEY `uq_data_source_name` (`data_source_name`)
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
    `product_date`   DATE NULL,
    `units_per_case` INT NOT NULL DEFAULT 1,
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
    `id_agreement`       INT NOT NULL AUTO_INCREMENT,
    `fk_id_brand`        INT NOT NULL,
    `fk_id_category`     INT NOT NULL,
    `fk_id_industrial`   INT NOT NULL,
    `fk_id_unit`         INT NOT NULL,
    `palier_group`       VARCHAR(255) NULL,
    `is_billed_per_case` TINYINT(1) NOT NULL DEFAULT 0,
    `start_date`         DATE NULL,
    `end_date`           DATE NULL,
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
    `id_agreement_tier` INT NOT NULL AUTO_INCREMENT,
    `fk_id_agreement`   INT NOT NULL,
    `min_uvc`           INT NOT NULL,
    `max_uvc`           INT DEFAULT NULL,
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
    `id_transaction`        INT NOT NULL AUTO_INCREMENT,
    `fk_id_product`         INT NULL,
    `fk_id_agreement`       INT NULL,
    `fk_id_agreement_tier`  INT NULL, -- Quel palier de l'accord - Historique
    `fk_id_distributor`     INT NULL,
    `quantity`              INT NOT NULL,
    `unit_price`            DECIMAL(10, 2) NOT NULL,
    `agreement_unit_price`  DECIMAL(10, 2) NULL, -- Quel prix unitaire de l'accord - Historique
    `total_price`           DECIMAL(10, 2) NOT NULL,
    `agreement_total_price` DECIMAL(10, 2) NULL, -- Quel prix total de l'accord - Historique + source des totaux
    `transaction_date`      DATE NULL,
    PRIMARY KEY (`id_transaction`),
    FOREIGN KEY (`fk_id_product`)
        REFERENCES `product`(`id_product`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_agreement`)
        REFERENCES `agreement`(`id_agreement`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_agreement_tier`)
        REFERENCES `agreement_tier`(`id_agreement_tier`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (`fk_id_distributor`)
        REFERENCES `distributor`(`id_distributor`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;
