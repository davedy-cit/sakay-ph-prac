/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ACCREDITATION` (
  `accreditation_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `badge_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `expiry_date` date NOT NULL,
  `badge_visible` tinyint(1) NOT NULL,
  `lgu_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `driver_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`accreditation_id`),
  UNIQUE KEY `badge_no` (`badge_no`),
  UNIQUE KEY `uq_accreditation_driver_lgu` (`driver_id`,`lgu_code`),
  KEY `ACCREDITATION_lgu_code_2285a56e_fk_LGU_UNIT_lgu_code` (`lgu_code`),
  CONSTRAINT `ACCREDITATION_driver_id_06ae6a28_fk_DRIVER_driver_id` FOREIGN KEY (`driver_id`) REFERENCES `DRIVER` (`driver_id`),
  CONSTRAINT `ACCREDITATION_lgu_code_2285a56e_fk_LGU_UNIT_lgu_code` FOREIGN KEY (`lgu_code`) REFERENCES `LGU_UNIT` (`lgu_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `CANCELLATION` (
  `cancel_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reason_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fee_amount` decimal(10,2) NOT NULL,
  `refund_amount` decimal(10,2) NOT NULL,
  `cancelled_at` datetime(6) NOT NULL,
  `cancelled_by` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`cancel_id`),
  UNIQUE KEY `ride_id` (`ride_id`),
  KEY `CANCELLATION_cancelled_by_a34f56b4_fk_USER_user_id` (`cancelled_by`),
  CONSTRAINT `CANCELLATION_cancelled_by_a34f56b4_fk_USER_user_id` FOREIGN KEY (`cancelled_by`) REFERENCES `USER` (`user_id`),
  CONSTRAINT `CANCELLATION_ride_id_8ebc7b38_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`),
  CONSTRAINT `ck_cancel_fee_nonneg` CHECK ((`fee_amount` >= 0)),
  CONSTRAINT `ck_cancel_refund_nonneg` CHECK ((`refund_amount` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `DRIVER` (
  `driver_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `license_number` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `accreditation_status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_online` tinyint(1) NOT NULL,
  `rating` decimal(2,1) DEFAULT NULL,
  `total_trips` int NOT NULL,
  PRIMARY KEY (`driver_id`),
  UNIQUE KEY `license_number` (`license_number`),
  KEY `idx_driver_avail` (`is_online`,`accreditation_status`),
  CONSTRAINT `DRIVER_driver_id_847dccb5_fk_USER_user_id` FOREIGN KEY (`driver_id`) REFERENCES `USER` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `DRIVER_PAYOUT` (
  `payout_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `gateway_ref` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `requested_at` datetime(6) NOT NULL,
  `paid_at` datetime(6) DEFAULT NULL,
  `driver_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `method_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`payout_id`),
  KEY `DRIVER_PAYOUT_method_code_ddc8961a_fk_PAYMENT_METHOD_method_code` (`method_code`),
  KEY `idx_payout_driver_status` (`driver_id`,`status`),
  CONSTRAINT `DRIVER_PAYOUT_driver_id_866afe7a_fk_DRIVER_driver_id` FOREIGN KEY (`driver_id`) REFERENCES `DRIVER` (`driver_id`),
  CONSTRAINT `DRIVER_PAYOUT_method_code_ddc8961a_fk_PAYMENT_METHOD_method_code` FOREIGN KEY (`method_code`) REFERENCES `PAYMENT_METHOD` (`method_code`),
  CONSTRAINT `ck_payout_amount_nonneg` CHECK ((`amount` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `FARE_SHARE` (
  `id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `passenger_count` smallint NOT NULL,
  `share_amount` decimal(10,2) NOT NULL,
  `is_paid` tinyint(1) NOT NULL,
  `group_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `passenger_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fareshare_payment_passenger` (`payment_id`,`passenger_id`),
  KEY `FARE_SHARE_group_id_81fcfe6b_fk_PAKYAWAN_GROUP_group_id` (`group_id`),
  KEY `FARE_SHARE_passenger_id_4963f17a_fk_PASSENGER_passenger_id` (`passenger_id`),
  CONSTRAINT `FARE_SHARE_group_id_81fcfe6b_fk_PAKYAWAN_GROUP_group_id` FOREIGN KEY (`group_id`) REFERENCES `PAKYAWAN_GROUP` (`group_id`),
  CONSTRAINT `FARE_SHARE_passenger_id_4963f17a_fk_PASSENGER_passenger_id` FOREIGN KEY (`passenger_id`) REFERENCES `PASSENGER` (`passenger_id`),
  CONSTRAINT `FARE_SHARE_payment_id_bb218584_fk_PAYMENT_payment_id` FOREIGN KEY (`payment_id`) REFERENCES `PAYMENT` (`payment_id`),
  CONSTRAINT `ck_fareshare_amount_nonneg` CHECK ((`share_amount` >= 0)),
  CONSTRAINT `ck_fareshare_count_positive` CHECK ((`passenger_count` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `LGU_UNIT` (
  `lgu_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lgu_name` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `province` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `region` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_no` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`lgu_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `LOCATION` (
  `location_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `street` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `barangay` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `city` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `province` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `landmark` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `latitude` decimal(9,6) NOT NULL,
  `longitude` decimal(9,6) NOT NULL,
  PRIMARY KEY (`location_id`),
  KEY `idx_location_area` (`city`,`barangay`),
  KEY `idx_location_geo` (`latitude`,`longitude`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PAKYAWAN_GROUP` (
  `group_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `direction` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `max_seats` smallint NOT NULL,
  `matched_seats` smallint NOT NULL,
  `group_status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `ride_id` (`ride_id`),
  KEY `idx_pakyawan_status` (`group_status`),
  CONSTRAINT `PAKYAWAN_GROUP_ride_id_342a2f5e_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`),
  CONSTRAINT `ck_pakyawan_seats_nonneg` CHECK ((`matched_seats` >= 0)),
  CONSTRAINT `ck_pakyawan_seats_within_capacity` CHECK ((`matched_seats` <= `max_seats`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PASSENGER` (
  `passenger_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `home_address` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gcash_number` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `verified_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`passenger_id`),
  CONSTRAINT `PASSENGER_passenger_id_dfae720d_fk_USER_user_id` FOREIGN KEY (`passenger_id`) REFERENCES `USER` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PASSENGER_PREFERRED_MODE` (
  `id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `preferred_rank` smallint NOT NULL,
  `mode_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `passenger_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_prefmode_passenger_mode` (`passenger_id`,`mode_code`),
  KEY `PASSENGER_PREFERRED__mode_code_fd3aa8ab_fk_RIDE_MODE` (`mode_code`),
  CONSTRAINT `PASSENGER_PREFERRED__mode_code_fd3aa8ab_fk_RIDE_MODE` FOREIGN KEY (`mode_code`) REFERENCES `RIDE_MODE` (`mode_code`),
  CONSTRAINT `PASSENGER_PREFERRED__passenger_id_90df7569_fk_PASSENGER` FOREIGN KEY (`passenger_id`) REFERENCES `PASSENGER` (`passenger_id`),
  CONSTRAINT `ck_prefmode_rank_positive` CHECK ((`preferred_rank` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PAYMENT` (
  `payment_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `gateway_ref` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `paid_at` datetime(6) NOT NULL,
  `payer_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `method_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `wallet_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`payment_id`),
  UNIQUE KEY `ride_id` (`ride_id`),
  KEY `PAYMENT_wallet_id_1adb4adb_fk_WALLET_wallet_id` (`wallet_id`),
  KEY `idx_payment_status` (`status`,`paid_at` DESC),
  KEY `idx_payment_payer` (`payer_id`,`paid_at` DESC),
  KEY `PAYMENT_method_code_4cd4eb10_fk_PAYMENT_METHOD_method_code` (`method_code`),
  CONSTRAINT `PAYMENT_method_code_4cd4eb10_fk_PAYMENT_METHOD_method_code` FOREIGN KEY (`method_code`) REFERENCES `PAYMENT_METHOD` (`method_code`),
  CONSTRAINT `PAYMENT_payer_id_e7d81698_fk_PASSENGER_passenger_id` FOREIGN KEY (`payer_id`) REFERENCES `PASSENGER` (`passenger_id`),
  CONSTRAINT `PAYMENT_ride_id_5a78da91_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`),
  CONSTRAINT `PAYMENT_wallet_id_1adb4adb_fk_WALLET_wallet_id` FOREIGN KEY (`wallet_id`) REFERENCES `WALLET` (`wallet_id`),
  CONSTRAINT `ck_payment_amount_nonneg` CHECK ((`amount` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PAYMENT_METHOD` (
  `method_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `method_name` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_digital` tinyint(1) NOT NULL,
  `gateway_name` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`method_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PLATFORM_CONFIG` (
  `key` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `value` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `RATING` (
  `rating_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stars` smallint NOT NULL,
  `comment` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rated_at` datetime(6) NOT NULL,
  `ratee_user_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rater_user_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`rating_id`),
  UNIQUE KEY `uq_rating_ride_rater` (`ride_id`,`rater_user_id`),
  KEY `RATING_rater_user_id_45aa0113_fk_USER_user_id` (`rater_user_id`),
  KEY `idx_rating_ratee` (`ratee_user_id`,`rated_at` DESC),
  CONSTRAINT `RATING_ratee_user_id_f77f9126_fk_USER_user_id` FOREIGN KEY (`ratee_user_id`) REFERENCES `USER` (`user_id`),
  CONSTRAINT `RATING_rater_user_id_45aa0113_fk_USER_user_id` FOREIGN KEY (`rater_user_id`) REFERENCES `USER` (`user_id`),
  CONSTRAINT `RATING_ride_id_2d795663_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`),
  CONSTRAINT `ck_rating_not_self` CHECK ((`rater_user_id` <> `ratee_user_id`)),
  CONSTRAINT `ck_rating_stars_1_to_5` CHECK (((`stars` >= 1) and (`stars` <= 5)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `RECEIPT` (
  `receipt_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `issued_at` datetime(6) NOT NULL,
  `receipt_url` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`receipt_no`),
  UNIQUE KEY `payment_id` (`payment_id`),
  CONSTRAINT `RECEIPT_payment_id_4a0ffce8_fk_PAYMENT_payment_id` FOREIGN KEY (`payment_id`) REFERENCES `PAYMENT` (`payment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `RIDE` (
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_trip_chain` tinyint(1) NOT NULL,
  `leg_count` smallint DEFAULT NULL,
  `fare_estimate` decimal(10,2) DEFAULT NULL,
  `request_time` datetime(6) NOT NULL,
  `matched_at` datetime(6) DEFAULT NULL,
  `ended_at` datetime(6) DEFAULT NULL,
  `driver_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dropoff_location_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mode_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `passenger_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pickup_location_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`ride_id`),
  KEY `idx_ride_pax_status` (`passenger_id`,`status`),
  KEY `idx_ride_drv_status` (`driver_id`,`status`),
  KEY `idx_ride_recent` (`request_time` DESC),
  KEY `RIDE_dropoff_location_id_6b8f6393_fk_LOCATION_location_id` (`dropoff_location_id`),
  KEY `RIDE_mode_code_4b7331b7_fk_RIDE_MODE_mode_code` (`mode_code`),
  KEY `RIDE_pickup_location_id_56cf3ca4_fk_LOCATION_location_id` (`pickup_location_id`),
  KEY `RIDE_vehicle_id_78c769bc_fk_VEHICLE_vehicle_id` (`vehicle_id`),
  CONSTRAINT `RIDE_driver_id_0d034fae_fk_DRIVER_driver_id` FOREIGN KEY (`driver_id`) REFERENCES `DRIVER` (`driver_id`),
  CONSTRAINT `RIDE_dropoff_location_id_6b8f6393_fk_LOCATION_location_id` FOREIGN KEY (`dropoff_location_id`) REFERENCES `LOCATION` (`location_id`),
  CONSTRAINT `RIDE_mode_code_4b7331b7_fk_RIDE_MODE_mode_code` FOREIGN KEY (`mode_code`) REFERENCES `RIDE_MODE` (`mode_code`),
  CONSTRAINT `RIDE_passenger_id_acb2db01_fk_PASSENGER_passenger_id` FOREIGN KEY (`passenger_id`) REFERENCES `PASSENGER` (`passenger_id`),
  CONSTRAINT `RIDE_pickup_location_id_56cf3ca4_fk_LOCATION_location_id` FOREIGN KEY (`pickup_location_id`) REFERENCES `LOCATION` (`location_id`),
  CONSTRAINT `RIDE_vehicle_id_78c769bc_fk_VEHICLE_vehicle_id` FOREIGN KEY (`vehicle_id`) REFERENCES `VEHICLE` (`vehicle_id`),
  CONSTRAINT `ck_ride_ended_after_request` CHECK (((`ended_at` is null) or (`ended_at` >= `request_time`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `RIDE_LEG` (
  `id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `leg_no` smallint NOT NULL,
  `fare` decimal(10,2) NOT NULL,
  `distance_km` decimal(6,2) DEFAULT NULL,
  `eta_minutes` smallint DEFAULT NULL,
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dest_location_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `driver_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mode_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `origin_location_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `surge_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_rideleg_ride_legno` (`ride_id`,`leg_no`),
  KEY `RIDE_LEG_dest_location_id_945dbb44_fk_LOCATION_location_id` (`dest_location_id`),
  KEY `RIDE_LEG_driver_id_68be2e3c_fk_DRIVER_driver_id` (`driver_id`),
  KEY `RIDE_LEG_mode_code_2a43c6c7_fk_RIDE_MODE_mode_code` (`mode_code`),
  KEY `RIDE_LEG_origin_location_id_10451e37_fk_LOCATION_location_id` (`origin_location_id`),
  KEY `RIDE_LEG_surge_id_ddadd465_fk_SURGE_PERIOD_surge_id` (`surge_id`),
  CONSTRAINT `RIDE_LEG_dest_location_id_945dbb44_fk_LOCATION_location_id` FOREIGN KEY (`dest_location_id`) REFERENCES `LOCATION` (`location_id`),
  CONSTRAINT `RIDE_LEG_driver_id_68be2e3c_fk_DRIVER_driver_id` FOREIGN KEY (`driver_id`) REFERENCES `DRIVER` (`driver_id`),
  CONSTRAINT `RIDE_LEG_mode_code_2a43c6c7_fk_RIDE_MODE_mode_code` FOREIGN KEY (`mode_code`) REFERENCES `RIDE_MODE` (`mode_code`),
  CONSTRAINT `RIDE_LEG_origin_location_id_10451e37_fk_LOCATION_location_id` FOREIGN KEY (`origin_location_id`) REFERENCES `LOCATION` (`location_id`),
  CONSTRAINT `RIDE_LEG_ride_id_10d0b313_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`),
  CONSTRAINT `RIDE_LEG_surge_id_ddadd465_fk_SURGE_PERIOD_surge_id` FOREIGN KEY (`surge_id`) REFERENCES `SURGE_PERIOD` (`surge_id`),
  CONSTRAINT `ck_rideleg_legno_positive` CHECK ((`leg_no` >= 1)),
  CONSTRAINT `ck_rideleg_origin_differs_from_dest` CHECK ((`origin_location_id` <> `dest_location_id`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `RIDE_MODE` (
  `mode_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mode_name` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `base_fare` decimal(8,2) NOT NULL,
  `per_km_rate` decimal(8,2) NOT NULL,
  `seat_capacity` smallint NOT NULL,
  `is_shared` tinyint(1) NOT NULL,
  `booking_fee` decimal(8,2) NOT NULL,
  PRIMARY KEY (`mode_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SOS_ALERT` (
  `alert_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alert_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alert_lat` decimal(9,6) NOT NULL,
  `alert_long` decimal(9,6) NOT NULL,
  `status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `triggered_at` datetime(6) NOT NULL,
  `resolved_at` datetime(6) DEFAULT NULL,
  `raised_by` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`alert_id`),
  UNIQUE KEY `ride_id` (`ride_id`),
  KEY `idx_sos_open` (`status`,`triggered_at` DESC),
  KEY `SOS_ALERT_raised_by_88a15494_fk_USER_user_id` (`raised_by`),
  CONSTRAINT `SOS_ALERT_raised_by_88a15494_fk_USER_user_id` FOREIGN KEY (`raised_by`) REFERENCES `USER` (`user_id`),
  CONSTRAINT `SOS_ALERT_ride_id_0063c35a_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`),
  CONSTRAINT `ck_sos_resolved_after_trigger` CHECK (((`resolved_at` is null) or (`resolved_at` >= `triggered_at`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SOS_NOTIFICATION` (
  `id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `notified_at` datetime(6) NOT NULL,
  `delivery_status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alert_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sosnotif_alert_contact` (`alert_id`,`contact_id`),
  KEY `SOS_NOTIFICATION_contact_id_47ca6c27_fk_TRUSTED_C` (`contact_id`),
  CONSTRAINT `SOS_NOTIFICATION_alert_id_db44da24_fk_SOS_ALERT_alert_id` FOREIGN KEY (`alert_id`) REFERENCES `SOS_ALERT` (`alert_id`),
  CONSTRAINT `SOS_NOTIFICATION_contact_id_47ca6c27_fk_TRUSTED_C` FOREIGN KEY (`contact_id`) REFERENCES `TRUSTED_CONTACT` (`contact_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SURGE_PERIOD` (
  `surge_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `surge_label` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `trigger_type` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `multiplier` decimal(4,2) NOT NULL,
  `starts_at` datetime(6) NOT NULL,
  `ends_at` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `lgu_code` varchar(12) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`surge_id`),
  KEY `idx_surge_window` (`is_active`,`starts_at`,`ends_at`),
  KEY `SURGE_PERIOD_lgu_code_b66d4e3e_fk_LGU_UNIT_lgu_code` (`lgu_code`),
  CONSTRAINT `SURGE_PERIOD_lgu_code_b66d4e3e_fk_LGU_UNIT_lgu_code` FOREIGN KEY (`lgu_code`) REFERENCES `LGU_UNIT` (`lgu_code`),
  CONSTRAINT `ck_surge_ends_after_starts` CHECK ((`ends_at` > `starts_at`)),
  CONSTRAINT `ck_surge_multiplier_min_1` CHECK ((`multiplier` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `TRIP_TRACKING` (
  `track_id` bigint NOT NULL AUTO_INCREMENT,
  `latitude` decimal(9,6) NOT NULL,
  `longitude` decimal(9,6) NOT NULL,
  `recorded_at` datetime(6) NOT NULL,
  `ride_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`track_id`),
  KEY `idx_tracking_latest` (`ride_id`,`recorded_at` DESC),
  CONSTRAINT `TRIP_TRACKING_ride_id_c538777d_fk_RIDE_ride_id` FOREIGN KEY (`ride_id`) REFERENCES `RIDE` (`ride_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `TRUSTED_CONTACT` (
  `contact_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_mobile` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `relationship` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `passenger_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`contact_id`),
  UNIQUE KEY `uq_contact_passenger_mobile` (`passenger_id`,`contact_mobile`),
  CONSTRAINT `TRUSTED_CONTACT_passenger_id_27899b73_fk_PASSENGER_passenger_id` FOREIGN KEY (`passenger_id`) REFERENCES `PASSENGER` (`passenger_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `USER` (
  `user_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `full_name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `registration_date` date NOT NULL,
  `user_role` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_status` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `phone` (`phone`),
  KEY `idx_user_role` (`user_role`),
  KEY `idx_user_status` (`account_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `USER_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `USER_groups_user_id_group_id_a18874a6_uniq` (`user_id`,`group_id`),
  KEY `USER_groups_group_id_e62f4720_fk_auth_group_id` (`group_id`),
  CONSTRAINT `USER_groups_group_id_e62f4720_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `USER_groups_user_id_c98bc129_fk_USER_user_id` FOREIGN KEY (`user_id`) REFERENCES `USER` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `USER_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `USER_user_permissions_user_id_permission_id_217489a1_uniq` (`user_id`,`permission_id`),
  KEY `USER_user_permission_permission_id_88c5bdfa_fk_auth_perm` (`permission_id`),
  CONSTRAINT `USER_user_permission_permission_id_88c5bdfa_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `USER_user_permissions_user_id_c8904d86_fk_USER_user_id` FOREIGN KEY (`user_id`) REFERENCES `USER` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `VEHICLE` (
  `vehicle_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `plate_number` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `capacity` smallint DEFAULT NULL,
  `route_info` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mode_code` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `driver_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`vehicle_id`),
  UNIQUE KEY `plate_number` (`plate_number`),
  UNIQUE KEY `driver_id` (`driver_id`),
  KEY `VEHICLE_mode_code_bfb67d49_fk_RIDE_MODE_mode_code` (`mode_code`),
  CONSTRAINT `VEHICLE_driver_id_c4fe876f_fk_DRIVER_driver_id` FOREIGN KEY (`driver_id`) REFERENCES `DRIVER` (`driver_id`),
  CONSTRAINT `VEHICLE_mode_code_bfb67d49_fk_RIDE_MODE_mode_code` FOREIGN KEY (`mode_code`) REFERENCES `RIDE_MODE` (`mode_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `WALLET` (
  `wallet_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `balance` decimal(12,2) NOT NULL,
  `currency` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `passenger_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`wallet_id`),
  UNIQUE KEY `passenger_id` (`passenger_id`),
  CONSTRAINT `WALLET_passenger_id_a4d915c2_fk_PASSENGER_passenger_id` FOREIGN KEY (`passenger_id`) REFERENCES `PASSENGER` (`passenger_id`),
  CONSTRAINT `ck_wallet_balance_nonneg` CHECK ((`balance` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `WALLET_TXN` (
  `txn_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `txn_type` varchar(12) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `balance_after` decimal(12,2) NOT NULL,
  `gateway_ref` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `payment_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wallet_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`txn_id`),
  KEY `idx_txn_wallet_recent` (`wallet_id`,`created_at` DESC),
  KEY `WALLET_TXN_payment_id_d3f09938_fk_PAYMENT_payment_id` (`payment_id`),
  CONSTRAINT `WALLET_TXN_payment_id_d3f09938_fk_PAYMENT_payment_id` FOREIGN KEY (`payment_id`) REFERENCES `PAYMENT` (`payment_id`),
  CONSTRAINT `WALLET_TXN_wallet_id_a32a5dd4_fk_WALLET_wallet_id` FOREIGN KEY (`wallet_id`) REFERENCES `WALLET` (`wallet_id`),
  CONSTRAINT `ck_txn_amount_nonneg` CHECK ((`amount` >= 0)),
  CONSTRAINT `ck_txn_balance_nonneg` CHECK ((`balance_after` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=129 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_USER_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_USER_user_id` FOREIGN KEY (`user_id`) REFERENCES `USER` (`user_id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
