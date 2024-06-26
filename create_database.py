from posgres_manager import Client
from private import database_detail


a = Client(**database_detail)


list_of_commands = [

{'query': """
    CREATE TABLE IF NOT EXISTS UserDetail (
    id SERIAL PRIMARY KEY,
    userID BIGINT NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    user_name VARCHAR(50),
    -- email VARCHAR(255),
    phone_number VARCHAR(15),
    credit BIGINT DEFAULT 0,
    entered_with_refral_link BIGINT DEFAULT NULL,
    number_of_invitations SMALLINT DEFAULT 0,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    referral_link VARCHAR(50),
    membership_status VARCHAR(50),
    discount_code VARCHAR(50),
    CONSTRAINT fk_referral FOREIGN KEY (entered_with_refral_link) REFERENCES UserDetail(userID) ON DELETE CASCADE
);
""", 'params': None},


{'query': """
    CREATE TABLE IF NOT EXISTS DiscountCode (
    discountID SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT TRUE,
    available_for_all_user BOOLEAN DEFAULT FALSE,
    for_userID BIGINT DEFAULT NULL,
    credit BIGINT DEFAULT 0 CHECK (credit > 0),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP NOT NULL,
    code VARCHAR(100) NOT NULL
    );
""", 'params': None},


{'query': """
    CREATE TABLE IF NOT EXISTS UseDiscount (
    usediscountID SERIAL PRIMARY KEY,
    discountID SMALLINT,
    userID BIGINT,
    code VARCHAR(100),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (userID) REFERENCES UserDetail(UserID) ON DELETE CASCADE,
    CONSTRAINT fk_discount FOREIGN KEY (discountID) REFERENCES DiscountCode(discountID) ON DELETE CASCADE
    );
""", 'params': None},


{'query': """

    CREATE TABLE IF NOT EXISTS Course (
    courseID SERIAL PRIMARY KEY,
    status BOOLEAN DEFAULT TRUE,
    content_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    cover_type VARCHAR(10),
    cover BYTEA,
    media BYTEA,
    channel_link TEXT,
    channel_chat_id TEXT,
    referral_requirement INT DEFAULT 0,
    discount_percent_per_invite INT DEFAULT 0,
    price BIGINT CHECK (price >= discount_percent),
    discount_percent SMALLINT DEFAULT 0 CHECK (discount_percent >= 0) CHECK (discount_percent <= 100),
    is_free BOOLEAN DEFAULT FALSE,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""", 'params': None},


{'query': """
    CREATE TABLE IF NOT EXISTS Admin (
    adminID SERIAL PRIMARY KEY,
    userID BIGINT,
    -- password_hash VARCHAR(255),
    -- email VARCHAR(255) NOT NULL UNIQUE,
    -- full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (userID) REFERENCES UserDetail(UserID) ON DELETE CASCADE
);
""", 'params': None},


{'query': """
    CREATE TABLE IF NOT EXISTS Invoice (
    invoiceID SERIAL PRIMARY KEY,
    userID BIGINT NOT NULL,
    course_ID BIGINT,
    discountID SMALLINT DEFAULT NULL,
    amount BIGINT NOT NULL,
    discount BIGINT DEFAULT 0,
    payment_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_method VARCHAR(50),
    payment_for VARCHAR(50),
    CONSTRAINT fk_user FOREIGN KEY (userID) REFERENCES UserDetail(userID) ON DELETE CASCADE,
    CONSTRAINT fk_course FOREIGN KEY (course_ID) REFERENCES Course(courseID) ON DELETE CASCADE,
    CONSTRAINT fk_discount FOREIGN KEY (discountID) REFERENCES DiscountCode(discountID) ON DELETE CASCADE
);""", 'params': None},


{'query': """
    CREATE TABLE IF NOT EXISTS Accept_Private_Channel (
    ID SERIAL PRIMARY KEY,
    status BOOLEAN DEFAULT FALSE,
    user_ID BIGINT NOT NULL,
    course_ID BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    period_minut SMALLINT NOT NULL,
    channel_chat_id BIGINT NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY (user_ID) REFERENCES UserDetail(userID) ON DELETE CASCADE,
    CONSTRAINT fk_course FOREIGN KEY (course_ID) REFERENCES Course(courseID) ON DELETE CASCADE
);""", 'params': None},
]

def create():
    result = a.execute('transaction', list_of_commands)
    print(result)

# create()
# a.execute('transaction', [{'query': 'drop table UserDetail', 'params': None}])
