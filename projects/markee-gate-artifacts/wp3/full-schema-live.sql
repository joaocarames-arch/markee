--
-- PostgreSQL database dump
--

\restrict o3NtxcDeqXsTWog8vNXTXFXZBW4JXEWgr8bQTC3dL7xnKPAQ6rbonvrR14vWFgZ

-- Dumped from database version 15.18
-- Dumped by pg_dump version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: app; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA app;


--
-- Name: core; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA core;


--
-- Name: events; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA events;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alert_deliveries; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.alert_deliveries (
    alert_id uuid,
    channel character varying(50) NOT NULL,
    recipient text NOT NULL,
    status character varying(50) NOT NULL,
    error_message text,
    sent_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: alerts; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.alerts (
    user_id uuid NOT NULL,
    watchlist_id uuid,
    watchlist_item_id uuid,
    trademark_id uuid,
    alert_type character varying(50) NOT NULL,
    similarity_score double precision,
    phonetic_score double precision,
    class_overlap_score double precision,
    title character varying(500) NOT NULL,
    body text,
    is_read boolean NOT NULL,
    is_dismissed boolean NOT NULL,
    sent_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: client_portfolios; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.client_portfolios (
    team_id uuid NOT NULL,
    client_name character varying(255) NOT NULL,
    client_email character varying(255),
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: deadlines; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.deadlines (
    trademark_id uuid NOT NULL,
    deadline_type character varying(100) NOT NULL,
    due_date date NOT NULL,
    description text,
    status character varying(50) NOT NULL,
    alert_dates date[],
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: prospection_opportunities; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.prospection_opportunities (
    trademark_id uuid NOT NULL,
    opportunity_type character varying(50) NOT NULL,
    holder_name character varying(500),
    holder_type character varying(50),
    holder_district character varying(100),
    holder_cae character varying(50),
    nice_classes integer[],
    expiry_date date,
    score double precision,
    is_exported boolean NOT NULL,
    exported_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: review_queue; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.review_queue (
    source character varying(32) NOT NULL,
    item_type character varying(64) NOT NULL,
    payload jsonb NOT NULL,
    reason text,
    confidence_score double precision,
    status character varying(16) NOT NULL,
    trademark_id uuid,
    document_id uuid,
    resolved_at timestamp with time zone,
    resolved_by uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: subscriptions; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.subscriptions (
    user_id uuid NOT NULL,
    stripe_customer_id character varying(255),
    stripe_subscription_id character varying(255),
    plan_type character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    max_marks integer NOT NULL,
    max_users integer NOT NULL,
    max_clients integer NOT NULL,
    features jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: team_members; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.team_members (
    team_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role character varying(50) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: teams; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.teams (
    name character varying(255) NOT NULL,
    owner_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.users (
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255),
    company_name character varying(255),
    telegram_chat_id character varying(64),
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: watchlist_items; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.watchlist_items (
    watchlist_id uuid NOT NULL,
    mark_text character varying(500) NOT NULL,
    nice_classes integer[],
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: watchlists; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.watchlists (
    user_id uuid NOT NULL,
    team_id uuid,
    client_portfolio_id uuid,
    name character varying(255) NOT NULL,
    similarity_threshold integer NOT NULL,
    phonetic_weight double precision NOT NULL,
    class_weight double precision NOT NULL,
    nice_classes_filter integer[],
    jurisdictions character varying[],
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.documents (
    trademark_id uuid,
    document_type character varying(64) NOT NULL,
    source_url text,
    storage_path text,
    file_hash character varying(64),
    publication_date date,
    language character varying(8),
    metadata jsonb,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: goods_services; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.goods_services (
    trademark_id uuid NOT NULL,
    nice_class_id uuid NOT NULL,
    term text NOT NULL,
    language character varying(8) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: holders; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.holders (
    source_id character varying(64) NOT NULL,
    name character varying(512) NOT NULL,
    address text,
    country character varying(2),
    type character varying(32),
    raw_data jsonb,
    confidence_score double precision,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_holders_type CHECK (((type)::text = ANY ((ARRAY['natural'::character varying, 'legal'::character varying])::text[])))
);


--
-- Name: nice_classes; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.nice_classes (
    class_number integer NOT NULL,
    description_pt text,
    description_en text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_nice_class_number CHECK (((class_number >= 1) AND (class_number <= 45)))
);


--
-- Name: representatives; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.representatives (
    source_id character varying(64) NOT NULL,
    name character varying(512) NOT NULL,
    address text,
    country character varying(2),
    type character varying(32),
    raw_data jsonb,
    confidence_score double precision,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_representatives_type CHECK (((type)::text = ANY ((ARRAY['natural'::character varying, 'legal'::character varying, 'association'::character varying])::text[])))
);


--
-- Name: source_runs; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.source_runs (
    source_id uuid NOT NULL,
    run_type character varying(32) NOT NULL,
    status character varying(16) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    items_processed integer NOT NULL,
    items_new integer NOT NULL,
    items_updated integer NOT NULL,
    items_failed integer NOT NULL,
    error_message text,
    cursor_value character varying(128),
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: sources; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.sources (
    name character varying(64) NOT NULL,
    source_type character varying(32) NOT NULL,
    base_url text,
    auth_method character varying(32),
    is_enabled boolean NOT NULL,
    priority integer NOT NULL,
    config_snapshot jsonb,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_sources_priority CHECK ((priority >= 1))
);


--
-- Name: trademark_holders; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.trademark_holders (
    trademark_id uuid NOT NULL,
    holder_id uuid NOT NULL,
    role character varying(32) NOT NULL,
    since_date date,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: trademark_representatives; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.trademark_representatives (
    trademark_id uuid NOT NULL,
    representative_id uuid NOT NULL,
    role character varying(32) NOT NULL,
    since_date date,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: trademark_versions; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.trademark_versions (
    trademark_id uuid NOT NULL,
    version_number integer NOT NULL,
    snapshot jsonb NOT NULL,
    diff_from_previous jsonb,
    change_source character varying(64) NOT NULL,
    change_type character varying(32) NOT NULL,
    raw_response_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: trademarks; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.trademarks (
    source_id character varying(100) NOT NULL,
    application_number character varying(100),
    application_date date,
    registration_number character varying(100),
    registration_date date,
    word_mark character varying(500),
    figurative_mark_url character varying(500),
    status character varying(100),
    renewal_status character varying(100),
    nice_classes integer[],
    applicants jsonb,
    representatives jsonb,
    goods_services text,
    jurisdiction character varying(50) NOT NULL,
    raw_data jsonb,
    update_date timestamp with time zone,
    confidence_score double precision,
    ingest_source_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: lifecycle_events; Type: TABLE; Schema: events; Owner: -
--

CREATE TABLE events.lifecycle_events (
    trademark_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    event_date date NOT NULL,
    deadline_date date,
    description text,
    source character varying(50) NOT NULL,
    source_reference character varying(128),
    page_number integer,
    source_excerpt text,
    confidence_score double precision,
    raw_data jsonb,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: alert_deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_deliveries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    alert_id uuid,
    channel character varying(50) NOT NULL,
    recipient text NOT NULL,
    status character varying(50) NOT NULL,
    error_message text,
    sent_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    watchlist_id uuid,
    watchlist_item_id uuid,
    trademark_id uuid,
    alert_type character varying(50) NOT NULL,
    similarity_score double precision,
    phonetic_score double precision,
    class_overlap_score double precision,
    title character varying(500) NOT NULL,
    body text,
    is_read boolean,
    is_dismissed boolean,
    sent_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    key_hash character varying(255) NOT NULL,
    name character varying(255),
    scopes character varying(100)[],
    last_used_at timestamp with time zone,
    expires_at timestamp with time zone,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: client_portfolios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_portfolios (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    client_name character varying(255) NOT NULL,
    client_email character varying(255),
    notes text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: deadlines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deadlines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    trademark_id uuid NOT NULL,
    deadline_type character varying(100) NOT NULL,
    due_date date NOT NULL,
    description text,
    status character varying(50) NOT NULL,
    alert_dates date[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: lifecycle_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lifecycle_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    trademark_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    event_date date NOT NULL,
    description text,
    source character varying(50) NOT NULL,
    raw_data jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: prospection_opportunities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prospection_opportunities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    trademark_id uuid NOT NULL,
    opportunity_type character varying(50) NOT NULL,
    holder_name character varying(500),
    holder_type character varying(50),
    holder_district character varying(100),
    holder_cae character varying(50),
    nice_classes integer[],
    expiry_date date,
    score double precision,
    is_exported boolean,
    exported_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscriptions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    stripe_customer_id character varying(255),
    stripe_subscription_id character varying(255),
    plan_type character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    max_marks integer NOT NULL,
    max_users integer NOT NULL,
    max_clients integer,
    features jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: team_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_members (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    owner_id uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: trademarks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trademarks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id character varying(100) NOT NULL,
    application_number character varying(100),
    application_date date,
    registration_number character varying(100),
    registration_date date,
    word_mark character varying(500),
    figurative_mark_url character varying(500),
    status character varying(100),
    renewal_status character varying(100),
    nice_classes integer[],
    applicants jsonb,
    representatives jsonb,
    goods_services text,
    jurisdiction character varying(50) NOT NULL,
    raw_data jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255),
    company_name character varying(255),
    telegram_chat_id character varying(64),
    is_active boolean,
    is_superuser boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: watchlist_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.watchlist_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    watchlist_id uuid NOT NULL,
    mark_text character varying(500) NOT NULL,
    nice_classes integer[],
    notes text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: watchlists; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.watchlists (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    team_id uuid,
    client_portfolio_id uuid,
    name character varying(255) NOT NULL,
    similarity_threshold integer NOT NULL,
    phonetic_weight double precision,
    class_weight double precision,
    nice_classes_filter integer[],
    jurisdictions character varying[],
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: api_responses; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.api_responses (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    source_id uuid NOT NULL,
    source_run_id uuid,
    endpoint text NOT NULL,
    request_params jsonb,
    response_status integer,
    response_headers jsonb,
    response_body jsonb,
    response_size_bytes integer,
    duration_ms integer,
    error_message text
)
PARTITION BY RANGE (created_at);


--
-- Name: alert_deliveries alert_deliveries_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alert_deliveries
    ADD CONSTRAINT alert_deliveries_pkey PRIMARY KEY (id);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: client_portfolios client_portfolios_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.client_portfolios
    ADD CONSTRAINT client_portfolios_pkey PRIMARY KEY (id);


--
-- Name: deadlines deadlines_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.deadlines
    ADD CONSTRAINT deadlines_pkey PRIMARY KEY (id);


--
-- Name: prospection_opportunities prospection_opportunities_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.prospection_opportunities
    ADD CONSTRAINT prospection_opportunities_pkey PRIMARY KEY (id);


--
-- Name: review_queue review_queue_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.review_queue
    ADD CONSTRAINT review_queue_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: team_members team_members_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.team_members
    ADD CONSTRAINT team_members_pkey PRIMARY KEY (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: team_members uq_team_members_team_user; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.team_members
    ADD CONSTRAINT uq_team_members_team_user UNIQUE (team_id, user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: watchlist_items watchlist_items_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlist_items
    ADD CONSTRAINT watchlist_items_pkey PRIMARY KEY (id);


--
-- Name: watchlists watchlists_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: goods_services goods_services_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.goods_services
    ADD CONSTRAINT goods_services_pkey PRIMARY KEY (id);


--
-- Name: holders holders_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.holders
    ADD CONSTRAINT holders_pkey PRIMARY KEY (id);


--
-- Name: nice_classes nice_classes_class_number_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.nice_classes
    ADD CONSTRAINT nice_classes_class_number_key UNIQUE (class_number);


--
-- Name: nice_classes nice_classes_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.nice_classes
    ADD CONSTRAINT nice_classes_pkey PRIMARY KEY (id);


--
-- Name: representatives representatives_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.representatives
    ADD CONSTRAINT representatives_pkey PRIMARY KEY (id);


--
-- Name: source_runs source_runs_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.source_runs
    ADD CONSTRAINT source_runs_pkey PRIMARY KEY (id);


--
-- Name: sources sources_name_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.sources
    ADD CONSTRAINT sources_name_key UNIQUE (name);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: trademark_holders trademark_holders_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_holders
    ADD CONSTRAINT trademark_holders_pkey PRIMARY KEY (trademark_id, holder_id, role);


--
-- Name: trademark_representatives trademark_representatives_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_representatives
    ADD CONSTRAINT trademark_representatives_pkey PRIMARY KEY (trademark_id, representative_id);


--
-- Name: trademark_versions trademark_versions_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_versions
    ADD CONSTRAINT trademark_versions_pkey PRIMARY KEY (id);


--
-- Name: trademarks trademarks_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademarks
    ADD CONSTRAINT trademarks_pkey PRIMARY KEY (id);


--
-- Name: trademark_versions uq_versions_trademark_version; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_versions
    ADD CONSTRAINT uq_versions_trademark_version UNIQUE (trademark_id, version_number);


--
-- Name: lifecycle_events lifecycle_events_pkey; Type: CONSTRAINT; Schema: events; Owner: -
--

ALTER TABLE ONLY events.lifecycle_events
    ADD CONSTRAINT lifecycle_events_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: alert_deliveries alert_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries
    ADD CONSTRAINT alert_deliveries_pkey PRIMARY KEY (id);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: api_keys api_keys_key_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: client_portfolios client_portfolios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_portfolios
    ADD CONSTRAINT client_portfolios_pkey PRIMARY KEY (id);


--
-- Name: deadlines deadlines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deadlines
    ADD CONSTRAINT deadlines_pkey PRIMARY KEY (id);


--
-- Name: lifecycle_events lifecycle_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lifecycle_events
    ADD CONSTRAINT lifecycle_events_pkey PRIMARY KEY (id);


--
-- Name: prospection_opportunities prospection_opportunities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prospection_opportunities
    ADD CONSTRAINT prospection_opportunities_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: team_members team_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_pkey PRIMARY KEY (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: trademarks trademarks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trademarks
    ADD CONSTRAINT trademarks_pkey PRIMARY KEY (id);


--
-- Name: trademarks trademarks_source_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trademarks
    ADD CONSTRAINT trademarks_source_id_key UNIQUE (source_id);


--
-- Name: team_members uq_team_members_team_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT uq_team_members_team_user UNIQUE (team_id, user_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: watchlist_items watchlist_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.watchlist_items
    ADD CONSTRAINT watchlist_items_pkey PRIMARY KEY (id);


--
-- Name: watchlists watchlists_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.watchlists
    ADD CONSTRAINT watchlists_pkey PRIMARY KEY (id);


--
-- Name: api_responses api_responses_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_responses
    ADD CONSTRAINT api_responses_pkey PRIMARY KEY (id, created_at);


--
-- Name: ix_app_subscriptions_stripe_customer_id; Type: INDEX; Schema: app; Owner: -
--

CREATE INDEX ix_app_subscriptions_stripe_customer_id ON app.subscriptions USING btree (stripe_customer_id);


--
-- Name: ix_app_users_email; Type: INDEX; Schema: app; Owner: -
--

CREATE UNIQUE INDEX ix_app_users_email ON app.users USING btree (email);


--
-- Name: ix_core_documents_file_hash; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_documents_file_hash ON core.documents USING btree (file_hash);


--
-- Name: ix_core_documents_trademark_id; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_documents_trademark_id ON core.documents USING btree (trademark_id);


--
-- Name: ix_core_goods_services_trademark_id; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_goods_services_trademark_id ON core.goods_services USING btree (trademark_id);


--
-- Name: ix_core_holders_name; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_holders_name ON core.holders USING btree (name);


--
-- Name: ix_core_holders_source_id; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_holders_source_id ON core.holders USING btree (source_id);


--
-- Name: ix_core_representatives_name; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_representatives_name ON core.representatives USING btree (name);


--
-- Name: ix_core_representatives_source_id; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_representatives_source_id ON core.representatives USING btree (source_id);


--
-- Name: ix_core_source_runs_source_id; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_source_runs_source_id ON core.source_runs USING btree (source_id);


--
-- Name: ix_core_source_runs_status; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_source_runs_status ON core.source_runs USING btree (status);


--
-- Name: ix_core_trademark_versions_trademark_id; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_trademark_versions_trademark_id ON core.trademark_versions USING btree (trademark_id);


--
-- Name: ix_core_trademarks_application_number; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_trademarks_application_number ON core.trademarks USING btree (application_number);


--
-- Name: ix_core_trademarks_jurisdiction; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_trademarks_jurisdiction ON core.trademarks USING btree (jurisdiction);


--
-- Name: ix_core_trademarks_source_id; Type: INDEX; Schema: core; Owner: -
--

CREATE UNIQUE INDEX ix_core_trademarks_source_id ON core.trademarks USING btree (source_id);


--
-- Name: ix_core_trademarks_update_date; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX ix_core_trademarks_update_date ON core.trademarks USING btree (update_date);


--
-- Name: ix_events_lifecycle_events_deadline_date; Type: INDEX; Schema: events; Owner: -
--

CREATE INDEX ix_events_lifecycle_events_deadline_date ON events.lifecycle_events USING btree (deadline_date);


--
-- Name: ix_events_lifecycle_events_event_type; Type: INDEX; Schema: events; Owner: -
--

CREATE INDEX ix_events_lifecycle_events_event_type ON events.lifecycle_events USING btree (event_type);


--
-- Name: ix_events_lifecycle_events_trademark_id; Type: INDEX; Schema: events; Owner: -
--

CREATE INDEX ix_events_lifecycle_events_trademark_id ON events.lifecycle_events USING btree (trademark_id);


--
-- Name: idx_alerts_composite_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_alerts_composite_score ON public.alerts USING btree (watchlist_id, similarity_score);


--
-- Name: idx_alerts_user_unread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_alerts_user_unread ON public.alerts USING btree (user_id, is_dismissed, created_at);


--
-- Name: idx_deadlines_due_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_deadlines_due_date ON public.deadlines USING btree (due_date, status);


--
-- Name: idx_lifecycle_events_trademark; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_events_trademark ON public.lifecycle_events USING btree (trademark_id, event_date);


--
-- Name: idx_prospection_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prospection_score ON public.prospection_opportunities USING btree (opportunity_type, score);


--
-- Name: idx_trademarks_jurisdiction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trademarks_jurisdiction ON public.trademarks USING btree (jurisdiction);


--
-- Name: idx_trademarks_wordmark; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trademarks_wordmark ON public.trademarks USING gin (word_mark public.gin_trgm_ops);


--
-- Name: ix_raw_api_responses_source_id; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX ix_raw_api_responses_source_id ON ONLY raw.api_responses USING btree (source_id);


--
-- Name: alert_deliveries alert_deliveries_alert_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alert_deliveries
    ADD CONSTRAINT alert_deliveries_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES app.alerts(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_trademark_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alerts
    ADD CONSTRAINT alerts_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alerts
    ADD CONSTRAINT alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alerts
    ADD CONSTRAINT alerts_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES app.watchlists(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_watchlist_item_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.alerts
    ADD CONSTRAINT alerts_watchlist_item_id_fkey FOREIGN KEY (watchlist_item_id) REFERENCES app.watchlist_items(id) ON DELETE SET NULL;


--
-- Name: client_portfolios client_portfolios_team_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.client_portfolios
    ADD CONSTRAINT client_portfolios_team_id_fkey FOREIGN KEY (team_id) REFERENCES app.teams(id) ON DELETE CASCADE;


--
-- Name: deadlines deadlines_trademark_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.deadlines
    ADD CONSTRAINT deadlines_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: prospection_opportunities prospection_opportunities_trademark_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.prospection_opportunities
    ADD CONSTRAINT prospection_opportunities_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: review_queue review_queue_resolved_by_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.review_queue
    ADD CONSTRAINT review_queue_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES app.users(id) ON DELETE SET NULL;


--
-- Name: review_queue review_queue_trademark_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.review_queue
    ADD CONSTRAINT review_queue_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE SET NULL;


--
-- Name: subscriptions subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.subscriptions
    ADD CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_team_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.team_members
    ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES app.teams(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.team_members
    ADD CONSTRAINT team_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;


--
-- Name: teams teams_owner_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.teams
    ADD CONSTRAINT teams_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES app.users(id);


--
-- Name: watchlist_items watchlist_items_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlist_items
    ADD CONSTRAINT watchlist_items_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES app.watchlists(id) ON DELETE CASCADE;


--
-- Name: watchlists watchlists_client_portfolio_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_client_portfolio_id_fkey FOREIGN KEY (client_portfolio_id) REFERENCES app.client_portfolios(id) ON DELETE SET NULL;


--
-- Name: watchlists watchlists_team_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_team_id_fkey FOREIGN KEY (team_id) REFERENCES app.teams(id) ON DELETE SET NULL;


--
-- Name: watchlists watchlists_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;


--
-- Name: documents documents_trademark_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.documents
    ADD CONSTRAINT documents_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id);


--
-- Name: goods_services goods_services_nice_class_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.goods_services
    ADD CONSTRAINT goods_services_nice_class_id_fkey FOREIGN KEY (nice_class_id) REFERENCES core.nice_classes(id);


--
-- Name: goods_services goods_services_trademark_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.goods_services
    ADD CONSTRAINT goods_services_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: source_runs source_runs_source_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.source_runs
    ADD CONSTRAINT source_runs_source_id_fkey FOREIGN KEY (source_id) REFERENCES core.sources(id);


--
-- Name: trademark_holders trademark_holders_holder_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_holders
    ADD CONSTRAINT trademark_holders_holder_id_fkey FOREIGN KEY (holder_id) REFERENCES core.holders(id) ON DELETE CASCADE;


--
-- Name: trademark_holders trademark_holders_trademark_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_holders
    ADD CONSTRAINT trademark_holders_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: trademark_representatives trademark_representatives_representative_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_representatives
    ADD CONSTRAINT trademark_representatives_representative_id_fkey FOREIGN KEY (representative_id) REFERENCES core.representatives(id) ON DELETE CASCADE;


--
-- Name: trademark_representatives trademark_representatives_trademark_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_representatives
    ADD CONSTRAINT trademark_representatives_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: trademark_versions trademark_versions_trademark_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademark_versions
    ADD CONSTRAINT trademark_versions_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: trademarks trademarks_ingest_source_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.trademarks
    ADD CONSTRAINT trademarks_ingest_source_id_fkey FOREIGN KEY (ingest_source_id) REFERENCES core.sources(id) ON DELETE SET NULL;


--
-- Name: lifecycle_events lifecycle_events_trademark_id_fkey; Type: FK CONSTRAINT; Schema: events; Owner: -
--

ALTER TABLE ONLY events.lifecycle_events
    ADD CONSTRAINT lifecycle_events_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES core.trademarks(id) ON DELETE CASCADE;


--
-- Name: alert_deliveries alert_deliveries_alert_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_deliveries
    ADD CONSTRAINT alert_deliveries_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES public.alerts(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_trademark_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES public.trademarks(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES public.watchlists(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_watchlist_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_watchlist_item_id_fkey FOREIGN KEY (watchlist_item_id) REFERENCES public.watchlist_items(id) ON DELETE SET NULL;


--
-- Name: api_keys api_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: client_portfolios client_portfolios_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_portfolios
    ADD CONSTRAINT client_portfolios_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: deadlines deadlines_trademark_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deadlines
    ADD CONSTRAINT deadlines_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES public.trademarks(id) ON DELETE CASCADE;


--
-- Name: lifecycle_events lifecycle_events_trademark_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lifecycle_events
    ADD CONSTRAINT lifecycle_events_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES public.trademarks(id) ON DELETE CASCADE;


--
-- Name: prospection_opportunities prospection_opportunities_trademark_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prospection_opportunities
    ADD CONSTRAINT prospection_opportunities_trademark_id_fkey FOREIGN KEY (trademark_id) REFERENCES public.trademarks(id) ON DELETE CASCADE;


--
-- Name: subscriptions subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: teams teams_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: watchlist_items watchlist_items_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.watchlist_items
    ADD CONSTRAINT watchlist_items_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES public.watchlists(id) ON DELETE CASCADE;


--
-- Name: watchlists watchlists_client_portfolio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.watchlists
    ADD CONSTRAINT watchlists_client_portfolio_id_fkey FOREIGN KEY (client_portfolio_id) REFERENCES public.client_portfolios(id) ON DELETE SET NULL;


--
-- Name: watchlists watchlists_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.watchlists
    ADD CONSTRAINT watchlists_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


--
-- Name: watchlists watchlists_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.watchlists
    ADD CONSTRAINT watchlists_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict o3NtxcDeqXsTWog8vNXTXFXZBW4JXEWgr8bQTC3dL7xnKPAQ6rbonvrR14vWFgZ

