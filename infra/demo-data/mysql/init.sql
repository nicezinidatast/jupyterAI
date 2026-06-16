-- Demo dataset for the crm connection. Loaded automatically by the official
-- mysql image when mounted under /docker-entrypoint-initdb.d/.

CREATE DATABASE IF NOT EXISTS crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE crm;

CREATE TABLE IF NOT EXISTS campaigns (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(128) NOT NULL,
    channel     VARCHAR(32)  NOT NULL,
    start_date  DATE         NOT NULL,
    end_date    DATE         NOT NULL,
    budget      DECIMAL(12,2) NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    lead_name    VARCHAR(128) NOT NULL,
    email        VARCHAR(256) NOT NULL,
    phone        VARCHAR(32)  NOT NULL,
    stage        VARCHAR(16)  NOT NULL,
    source       VARCHAR(32)  NOT NULL,
    campaign_id  INT          NULL,
    score        INT          NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_leads_stage (stage),
    INDEX idx_leads_campaign (campaign_id)
);

-- Generate 100 campaigns using a recursive CTE-equivalent procedure
DELIMITER //
DROP PROCEDURE IF EXISTS seed_campaigns//
CREATE PROCEDURE seed_campaigns()
BEGIN
    DECLARE g INT DEFAULT 1;
    WHILE g <= 100 DO
        INSERT INTO campaigns (name, channel, start_date, end_date, budget)
        VALUES (
            CONCAT('Campaign-', g),
            ELT((g % 4) + 1, 'email', 'sms', 'web', 'social'),
            DATE_SUB(CURDATE(), INTERVAL (g * 5 MOD 365) DAY),
            DATE_ADD(CURDATE(), INTERVAL ((g * 7) MOD 90) DAY),
            ROUND((100000 + (g * 1337) MOD 9000000) / 100, 2)
        );
        SET g = g + 1;
    END WHILE;
END//
DROP PROCEDURE IF EXISTS seed_leads//
CREATE PROCEDURE seed_leads()
BEGIN
    DECLARE g INT DEFAULT 1;
    WHILE g <= 1500 DO
        INSERT INTO leads (lead_name, email, phone, stage, source, campaign_id, score)
        VALUES (
            CONCAT(
              ELT((g MOD 12) + 1,
                  'Park Min-jun','Kim Ji-soo','Lee Seo-yeon','Choi Eun-woo',
                  'Jung Ha-yoon','Kang Do-yoon','Yoon Si-ah','Han Yu-jin',
                  'Cho Da-eun','Im Joon-ho','Seo Min-ji','Bae Hye-rin'),
              ' ', g
            ),
            CONCAT('lead', LPAD(g, 6, '0'), '@crm.example'),
            CONCAT('010-', LPAD(((g * 31) MOD 10000), 4, '0'),
                   '-', LPAD(((g * 47) MOD 10000), 4, '0')),
            ELT((g MOD 4) + 1, 'new', 'qualified', 'won', 'lost'),
            ELT((g MOD 4) + 1, 'web', 'referral', 'event', 'cold_call'),
            (g MOD 100) + 1,
            (g * 13) MOD 100
        );
        SET g = g + 1;
    END WHILE;
END//
DELIMITER ;

CALL seed_campaigns();
CALL seed_leads();
DROP PROCEDURE seed_campaigns;
DROP PROCEDURE seed_leads;
