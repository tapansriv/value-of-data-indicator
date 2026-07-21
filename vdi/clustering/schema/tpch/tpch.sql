SET DATABASE = tpch;

create table nation(
    n_nationkey       INTEGER NOT NULL PRIMARY KEY,
    n_name            CHAR(25) NOT NULL,
    n_regionkey       INTEGER NOT NULL,
    n_comment         VARCHAR(152)
);

create table region(
    r_regionkey       INTEGER NOT NULL PRIMARY KEY,
    r_name            CHAR(25) NOT NULL,
    r_comment         VARCHAR(152)
);

create table part(
    p_partkey         INTEGER NOT NULL PRIMARY KEY,
    p_name            VARCHAR(55) NOT NULL,
    p_mfgr            CHAR(25) NOT NULL,
    p_brand           CHAR(10) NOT NULL,
    p_type            VARCHAR(25) NOT NULL,
    p_size            INTEGER NOT NULL,
    p_container       CHAR(10) NOT NULL,
    p_retailprice     FLOAT NOT NULL,
    p_comment         VARCHAR(23) NOT NULL
);

create table supplier(
    s_suppkey         INTEGER NOT NULL PRIMARY KEY,
    s_name            CHAR(25) NOT NULL,
    s_address         VARCHAR(40) NOT NULL,
    s_nationkey       INTEGER NOT NULL,
    s_phone           CHAR(15) NOT NULL,
    s_acctbal         FLOAT NOT NULL,
    s_comment         VARCHAR(101) NOT NULL
);

create table partsupp(
    ps_partkey            INTEGER NOT NULL,
    ps_suppkey            INTEGER NOT NULL,
    ps_availqty           INTEGER NOT NULL,
    ps_supplycost         FLOAT NOT NULL,
    ps_comment            VARCHAR(199) NOT NULL,
    PRIMARY KEY (ps_partkey ASC, ps_suppkey ASC)
);

create table customer(
    c_custkey         INTEGER NOT NULL PRIMARY KEY,
    c_name            VARCHAR(25) NOT NULL,
    c_address         VARCHAR(40) NOT NULL,
    c_nationkey       INTEGER NOT NULL,
    c_phone           CHAR(15) NOT NULL,
    c_acctbal         FLOAT NOT NULL,
    c_mktsegment      CHAR(10) NOT NULL,
    c_comment         VARCHAR(117) NOT NULL
);

create table orders(
    o_orderkey           INTEGER NOT NULL PRIMARY KEY,
    o_custkey            INTEGER NOT NULL,
    o_orderstatus        CHAR(1) NOT NULL,
    o_totalprice         FLOAT NOT NULL,
    o_orderdate          DATE NOT NULL,
    o_orderpriority      CHAR(15) NOT NULL,
    o_clerk              CHAR(15) NOT NULL,
    o_shippriority       INTEGER NOT NULL,
    o_comment            VARCHAR(79) NOT NULL
);

create table lineitem(
    l_orderkey      INTEGER NOT NULL,
    l_partkey       INTEGER NOT NULL,
    l_suppkey       INTEGER NOT NULL,
    l_linenumber    INTEGER NOT NULL,
    l_quantity      FLOAT NOT NULL,
    l_extendedprice FLOAT NOT NULL,
    l_discount      FLOAT NOT NULL,
    l_tax           FLOAT NOT NULL,
    l_returnflag    CHAR(1) NOT NULL,
    l_linestatus    CHAR(1) NOT NULL,
    l_shipdate      DATE NOT NULL,
    l_commitdate    DATE NOT NULL,
    l_receiptdate   DATE NOT NULL,
    l_shipinstruct  CHAR(25) NOT NULL,
    l_shipmode      CHAR(10) NOT NULL,
    l_comment       VARCHAR(44) NOT NULL,
    PRIMARY KEY (l_orderkey, l_linenumber)
);
