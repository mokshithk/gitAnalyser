-- CodeProvenance Database Schema
-- Target: MariaDB / MySQL (XAMPP)

CREATE DATABASE IF NOT EXISTS `codeprovenance` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `codeprovenance`;

CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(255) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` VARCHAR(50) NOT NULL DEFAULT 'user',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `analyses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `input_type` VARCHAR(50) NOT NULL, -- 'git_url', 'zip', 'batch'
    `source` VARCHAR(512) NOT NULL,
    `mode` VARCHAR(50) NOT NULL DEFAULT 'full', -- 'full', 'similarity_only'
    `status` VARCHAR(50) NOT NULL DEFAULT 'queued', -- 'queued', 'cloning', 'parsing', 'comparing', 'done', 'failed'
    `error_message` TEXT NULL,
    `options` LONGTEXT NULL, -- JSON formatted options
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `finished_at` DATETIME NULL,
    CONSTRAINT `fk_analyses_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `commits` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `analysis_id` INT NOT NULL,
    `sha` VARCHAR(64) NOT NULL,
    `author_name` VARCHAR(255) NOT NULL,
    `author_email` VARCHAR(255) NOT NULL,
    `author_date` DATETIME NOT NULL,
    `commit_date` DATETIME NOT NULL,
    `lines_added` INT NOT NULL DEFAULT 0,
    `lines_deleted` INT NOT NULL DEFAULT 0,
    `files_changed` INT NOT NULL DEFAULT 0,
    `message` TEXT NOT NULL,
    INDEX `idx_commits_analysis` (`analysis_id`),
    CONSTRAINT `fk_commits_analyses` FOREIGN KEY (`analysis_id`) REFERENCES `analyses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `similarity_matches` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `analysis_id` INT NOT NULL,
    `target_type` VARCHAR(50) NOT NULL, -- 'corpus', 'previous_analysis', 'batch_peer'
    `target_ref` VARCHAR(512) NOT NULL,
    `score` FLOAT NOT NULL,
    `details` LONGTEXT NULL, -- JSON formatted details
    INDEX `idx_matches_analysis` (`analysis_id`),
    CONSTRAINT `fk_matches_analyses` FOREIGN KEY (`analysis_id`) REFERENCES `analyses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `flags` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `analysis_id` INT NOT NULL,
    `type` VARCHAR(100) NOT NULL,
    `severity` VARCHAR(50) NOT NULL, -- 'low', 'medium', 'high'
    `confidence` FLOAT NOT NULL DEFAULT 1.0,
    `title` VARCHAR(255) NOT NULL,
    `evidence` LONGTEXT NULL, -- JSON formatted evidence breakdown
    `review_status` VARCHAR(50) NOT NULL DEFAULT 'open', -- 'open', 'reviewed', 'dismissed'
    `note` TEXT NULL,
    INDEX `idx_flags_analysis` (`analysis_id`),
    CONSTRAINT `fk_flags_analyses` FOREIGN KEY (`analysis_id`) REFERENCES `analyses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `reference_corpus` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `repo_url` VARCHAR(512) NOT NULL UNIQUE,
    `language` VARCHAR(50) NOT NULL DEFAULT 'python',
    `added_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
