--
-- PostgreSQL database dump
--

\restrict 8YysdqlEngFnY7dtLwWcbgCHnRSwBgdppo7TiqGYrxPALvLLyvQ1MoKvehDLxdb

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
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

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

\unrestrict 8YysdqlEngFnY7dtLwWcbgCHnRSwBgdppo7TiqGYrxPALvLLyvQ1MoKvehDLxdb

