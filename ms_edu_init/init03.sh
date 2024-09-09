#!/bin/bash

psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
psql -U postgres -c "create database $DB_DATABASE with owner $DB_USER;"
psql -U postgres -d $DB_DATABASE -c "create table user_emails(id serial primary key, email varchar(256) not null);"
psql -U postgres -d $DB_DATABASE -c "ALTER TABLE user_emails OWNER TO $DB_USER;"
psql -U postgres -d $DB_DATABASE -c "create table user_phones(id serial primary key, phone varchar(256) not null);"
psql -U postgres -d $DB_DATABASE -c "ALTER TABLE user_phones OWNER TO $DB_USER;"
psql -U postgres -d $DB_DATABASE -c "CREATE USER $DB_REPL_USER REPLICATION LOGIN ENCRYPTED PASSWORD '$DB_REPL_PASSWORD';"
