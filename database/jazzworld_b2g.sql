-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 02, 2026 at 12:00 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `jazzworld_b2g`
--

-- --------------------------------------------------------

--
-- Table structure for table `coordinators`
--

CREATE TABLE `coordinators` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `region_id` int(10) UNSIGNED NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `coordinators`
--

INSERT INTO `coordinators` (`id`, `user_id`, `region_id`, `created_at`, `updated_at`) VALUES
(1, 2, 1, '2026-09-30 07:37:34', '2026-09-30 07:37:34');

-- --------------------------------------------------------

--
-- Table structure for table `employees`
--

CREATE TABLE `employees` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `employee_code` varchar(100) NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `region_id` int(10) UNSIGNED NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `employees`
--

INSERT INTO `employees` (`id`, `employee_code`, `name`, `email`, `region_id`, `is_active`, `created_at`, `updated_at`) VALUES
(1, 'EMP-C', 'Hamza Malik', 'hamza.malik@jazzworld.com', 3, 1, '2026-09-30 09:54:39', '2026-09-30 09:54:39'),
(2, 'EMP-N1', 'Ali Khan', 'ali.khan@jazzworld.com', 1, 1, '2026-09-30 09:54:39', '2026-09-30 09:54:39'),
(3, 'EMP-N2', 'Usman Ahmed', 'usman.ahmed@jazzworld.com', 2, 1, '2026-09-30 09:54:39', '2026-09-30 09:54:39'),
(4, 'EMP-S', 'Bilal Shah', 'bilal.shah@jazzworld.com', 4, 1, '2026-09-30 09:54:39', '2026-09-30 09:54:39');

-- --------------------------------------------------------

--
-- Table structure for table `products`
--

CREATE TABLE `products` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(100) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `products`
--

INSERT INTO `products` (`id`, `name`, `is_active`, `created_at`, `updated_at`) VALUES
(1, 'GSM', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50'),
(2, 'Fixed', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50'),
(3, 'Devices', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50'),
(4, 'M2M', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50'),
(5, 'SI', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50'),
(6, 'CMT', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50'),
(7, 'CPaas', 1, '2026-09-28 10:52:50', '2026-09-28 10:52:50');

-- --------------------------------------------------------

--
-- Table structure for table `regions`
--

CREATE TABLE `regions` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `regions`
--

INSERT INTO `regions` (`id`, `name`, `created_at`, `updated_at`) VALUES
(1, 'North1', '2026-09-30 07:33:59', '2026-09-30 07:33:59'),
(2, 'North2', '2026-09-30 07:33:59', '2026-09-30 07:33:59'),
(3, 'Central', '2026-09-30 07:33:59', '2026-09-30 07:33:59'),
(4, 'South', '2026-09-30 07:33:59', '2026-09-30 07:33:59');

-- --------------------------------------------------------

--
-- Table structure for table `roles`
--

CREATE TABLE `roles` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `roles`
--

INSERT INTO `roles` (`id`, `name`, `created_at`, `updated_at`) VALUES
(1, 'ADMIN', '2026-09-23 10:24:20', '2026-09-23 10:24:20'),
(2, 'COORDINATOR', '2026-09-23 10:24:20', '2026-09-23 10:24:20'),
(3, 'VIEWER', '2026-09-23 10:24:20', '2026-09-23 10:24:20');

-- --------------------------------------------------------

--
-- Table structure for table `tenders`
--

CREATE TABLE `tenders` (
  `jazzid` bigint(20) UNSIGNED NOT NULL,
  `source_id` int(10) UNSIGNED NOT NULL,
  `region_id` int(10) UNSIGNED DEFAULT NULL,
  `web_tender_no` varchar(255) DEFAULT NULL,
  `tender_reference_no` varchar(255) DEFAULT NULL,
  `tender_name` text DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `authority` varchar(500) DEFAULT NULL,
  `organization` varchar(500) DEFAULT NULL,
  `estimated_value` decimal(18,2) DEFAULT NULL,
  `estimated_value_source` varchar(100) DEFAULT NULL,
  `advertised_date` datetime DEFAULT NULL,
  `closed_date` datetime DEFAULT NULL,
  `source_detail_url` text DEFAULT NULL,
  `primary_document_url` text DEFAULT NULL,
  `raw_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`raw_data`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tender_documents`
--

CREATE TABLE `tender_documents` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tender_jazzid` bigint(20) UNSIGNED NOT NULL,
  `document_type` varchar(100) NOT NULL,
  `document_name` varchar(500) DEFAULT NULL,
  `source_url` text DEFAULT NULL,
  `local_path` text DEFAULT NULL,
  `download_status` varchar(50) NOT NULL DEFAULT 'PENDING',
  `file_size` bigint(20) UNSIGNED DEFAULT NULL,
  `downloaded_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tender_field_overrides`
--

CREATE TABLE `tender_field_overrides` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tender_jazzid` bigint(20) UNSIGNED NOT NULL,
  `web_tender_no` varchar(255) DEFAULT NULL,
  `tender_reference_no` varchar(255) DEFAULT NULL,
  `tender_name` text DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `authority` varchar(500) DEFAULT NULL,
  `organization` varchar(500) DEFAULT NULL,
  `estimated_value` decimal(18,2) DEFAULT NULL,
  `estimated_value_source` varchar(100) DEFAULT NULL,
  `advertised_date` datetime DEFAULT NULL,
  `closed_date` datetime DEFAULT NULL,
  `source_detail_url` text DEFAULT NULL,
  `primary_document_url` text DEFAULT NULL,
  `overridden_by` bigint(20) UNSIGNED DEFAULT NULL,
  `overridden_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tender_participation`
--

CREATE TABLE `tender_participation` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tender_jazzid` bigint(20) UNSIGNED NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'NOT_REVIEWED',
  `decided_by` bigint(20) UNSIGNED DEFAULT NULL,
  `decided_at` timestamp NULL DEFAULT NULL,
  `delegated_employee_id` bigint(20) UNSIGNED DEFAULT NULL,
  `product_ids` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`product_ids`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tender_region_assignments`
--

CREATE TABLE `tender_region_assignments` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tender_jazzid` bigint(20) UNSIGNED NOT NULL,
  `region_id` int(10) UNSIGNED NOT NULL,
  `assignment_type` enum('AUTO','ADMIN') NOT NULL,
  `assigned_by` bigint(20) UNSIGNED DEFAULT NULL,
  `assigned_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tender_relevance`
--

CREATE TABLE `tender_relevance` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tender_jazzid` bigint(20) UNSIGNED NOT NULL,
  `keyword_score` decimal(10,4) NOT NULL DEFAULT 0.0000,
  `matched_keywords` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`matched_keywords`)),
  `matched_capabilities` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`matched_capabilities`)),
  `relevance_reason` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tender_sources`
--

CREATE TABLE `tender_sources` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `tender_sources`
--

INSERT INTO `tender_sources` (`id`, `name`, `created_at`, `updated_at`) VALUES
(1, 'Federal PPRA', '2026-09-30 07:34:08', '2026-09-30 07:34:08'),
(2, 'KP PPRA', '2026-09-30 07:34:08', '2026-09-30 07:34:08'),
(3, 'Punjab PPRA', '2026-09-30 07:34:08', '2026-09-30 07:34:08'),
(4, 'Sindh PPRA', '2026-09-30 07:34:08', '2026-09-30 07:34:08'),
(5, 'Balochistan PPRA', '2026-09-30 07:34:08', '2026-09-30 07:34:08');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `role_id` int(10) UNSIGNED NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `password_hash`, `name`, `email`, `role_id`, `is_active`, `created_at`, `updated_at`) VALUES
(1, 'admin', '$2b$12$bD1IwtZrDSLiJptqWndsDuUVUj.swFb5SoXW6yBvG9P6vyPbL54Da', 'System Administrator', NULL, 1, 1, '2026-09-24 17:36:16', '2026-09-24 17:36:16'),
(2, 'coordinator_north1', '$2b$12$Sv2D5nfpgO8pRl4xwPzvTeQMOQKoYekROaj2UXOgYmPbxMj/5j.Om', 'North Coordinator', 'raza.najam@jazz.com.pk', 2, 1, '2026-09-24 18:25:49', '2026-10-02 09:55:39'),
(3, 'viewer', '$2b$12$nu2T605VwsTQW0kLF/D02ONhqvhvnGiXoVNKExoLWp74PJ5i5O00S', 'Viewer', 'viewer@jazzworld.local', 3, 1, '2026-09-24 19:03:25', '2026-09-24 19:03:25');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `coordinators`
--
ALTER TABLE `coordinators`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_coordinators_user` (`user_id`),
  ADD UNIQUE KEY `uq_coordinators_region` (`region_id`);

--
-- Indexes for table `employees`
--
ALTER TABLE `employees`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `employee_code` (`employee_code`),
  ADD KEY `idx_employees_region` (`region_id`);

--
-- Indexes for table `products`
--
ALTER TABLE `products`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `regions`
--
ALTER TABLE `regions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `roles`
--
ALTER TABLE `roles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `tenders`
--
ALTER TABLE `tenders`
  ADD PRIMARY KEY (`jazzid`),
  ADD KEY `idx_tenders_source_id` (`source_id`),
  ADD KEY `idx_tenders_web_tender_no` (`web_tender_no`),
  ADD KEY `idx_tenders_advertised_date` (`advertised_date`),
  ADD KEY `idx_tenders_closed_date` (`closed_date`),
  ADD KEY `idx_tenders_region_id` (`region_id`);

--
-- Indexes for table `tender_documents`
--
ALTER TABLE `tender_documents`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tender_documents_tender` (`tender_jazzid`),
  ADD KEY `idx_tender_documents_status` (`download_status`);

--
-- Indexes for table `tender_field_overrides`
--
ALTER TABLE `tender_field_overrides`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_tender_field_overrides_tender` (`tender_jazzid`),
  ADD KEY `fk_tender_field_overrides_user` (`overridden_by`);

--
-- Indexes for table `tender_participation`
--
ALTER TABLE `tender_participation`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_tender_participation_tender` (`tender_jazzid`),
  ADD KEY `idx_tender_participation_status` (`status`),
  ADD KEY `idx_tender_participation_user` (`decided_by`),
  ADD KEY `idx_tender_participation_employee` (`delegated_employee_id`);

--
-- Indexes for table `tender_region_assignments`
--
ALTER TABLE `tender_region_assignments`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_tra_user` (`assigned_by`),
  ADD KEY `idx_tra_tender_jazzid` (`tender_jazzid`),
  ADD KEY `idx_tra_region_id` (`region_id`),
  ADD KEY `idx_tra_assignment_type` (`assignment_type`);

--
-- Indexes for table `tender_relevance`
--
ALTER TABLE `tender_relevance`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_tender_relevance_tender` (`tender_jazzid`);

--
-- Indexes for table `tender_sources`
--
ALTER TABLE `tender_sources`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD KEY `idx_users_role` (`role_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `coordinators`
--
ALTER TABLE `coordinators`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `employees`
--
ALTER TABLE `employees`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `products`
--
ALTER TABLE `products`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `regions`
--
ALTER TABLE `regions`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `roles`
--
ALTER TABLE `roles`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `tenders`
--
ALTER TABLE `tenders`
  MODIFY `jazzid` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2213;

--
-- AUTO_INCREMENT for table `tender_documents`
--
ALTER TABLE `tender_documents`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1970;

--
-- AUTO_INCREMENT for table `tender_field_overrides`
--
ALTER TABLE `tender_field_overrides`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `tender_participation`
--
ALTER TABLE `tender_participation`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `tender_region_assignments`
--
ALTER TABLE `tender_region_assignments`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2164;

--
-- AUTO_INCREMENT for table `tender_relevance`
--
ALTER TABLE `tender_relevance`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2213;

--
-- AUTO_INCREMENT for table `tender_sources`
--
ALTER TABLE `tender_sources`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `coordinators`
--
ALTER TABLE `coordinators`
  ADD CONSTRAINT `fk_coordinators_region` FOREIGN KEY (`region_id`) REFERENCES `regions` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_coordinators_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `employees`
--
ALTER TABLE `employees`
  ADD CONSTRAINT `fk_employees_region` FOREIGN KEY (`region_id`) REFERENCES `regions` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `tenders`
--
ALTER TABLE `tenders`
  ADD CONSTRAINT `fk_tenders_region` FOREIGN KEY (`region_id`) REFERENCES `regions` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_tenders_source` FOREIGN KEY (`source_id`) REFERENCES `tender_sources` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `tender_documents`
--
ALTER TABLE `tender_documents`
  ADD CONSTRAINT `fk_tender_documents_tender` FOREIGN KEY (`tender_jazzid`) REFERENCES `tenders` (`jazzid`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `tender_field_overrides`
--
ALTER TABLE `tender_field_overrides`
  ADD CONSTRAINT `fk_tender_field_overrides_tender` FOREIGN KEY (`tender_jazzid`) REFERENCES `tenders` (`jazzid`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_tender_field_overrides_user` FOREIGN KEY (`overridden_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `tender_participation`
--
ALTER TABLE `tender_participation`
  ADD CONSTRAINT `fk_tender_participation_employee` FOREIGN KEY (`delegated_employee_id`) REFERENCES `employees` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_tender_participation_tender` FOREIGN KEY (`tender_jazzid`) REFERENCES `tenders` (`jazzid`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_tender_participation_user` FOREIGN KEY (`decided_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `tender_region_assignments`
--
ALTER TABLE `tender_region_assignments`
  ADD CONSTRAINT `fk_tra_region` FOREIGN KEY (`region_id`) REFERENCES `regions` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_tra_tender` FOREIGN KEY (`tender_jazzid`) REFERENCES `tenders` (`jazzid`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_tra_user` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `tender_relevance`
--
ALTER TABLE `tender_relevance`
  ADD CONSTRAINT `fk_tender_relevance_tender` FOREIGN KEY (`tender_jazzid`) REFERENCES `tenders` (`jazzid`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `users`
--
ALTER TABLE `users`
  ADD CONSTRAINT `fk_users_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
