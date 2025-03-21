-- PostgreSQL建表语句和模拟数据生成

-- 删除已存在的表（如果存在）
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 创建用户表
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    real_name VARCHAR(50),
    gender VARCHAR(10),
    birth_date DATE,
    address TEXT,
    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_time TIMESTAMP,
    status SMALLINT DEFAULT 1
);

-- 为PostgreSQL添加列注释
COMMENT ON COLUMN users.user_id IS '用户ID';
COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users.password IS '密码';
COMMENT ON COLUMN users.email IS '电子邮箱';
COMMENT ON COLUMN users.phone IS '手机号码';
COMMENT ON COLUMN users.real_name IS '真实姓名';
COMMENT ON COLUMN users.gender IS '性别';
COMMENT ON COLUMN users.birth_date IS '出生日期';
COMMENT ON COLUMN users.address IS '地址';
COMMENT ON COLUMN users.registration_time IS '注册时间';
COMMENT ON COLUMN users.last_login_time IS '最后登录时间';
COMMENT ON COLUMN users.status IS '状态：1-正常，0-禁用';

-- 创建商品表
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    description TEXT,
    image_url VARCHAR(255),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status SMALLINT DEFAULT 1
);

-- 为PostgreSQL添加列注释
COMMENT ON COLUMN products.product_id IS '商品ID';
COMMENT ON COLUMN products.product_name IS '商品名称';
COMMENT ON COLUMN products.category IS '商品类别';
COMMENT ON COLUMN products.price IS '商品价格';
COMMENT ON COLUMN products.stock IS '库存数量';
COMMENT ON COLUMN products.description IS '商品描述';
COMMENT ON COLUMN products.image_url IS '商品图片URL';
COMMENT ON COLUMN products.create_time IS '创建时间';
COMMENT ON COLUMN products.update_time IS '更新时间';
COMMENT ON COLUMN products.status IS '状态：1-上架，0-下架';

-- 创建订单表
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    order_number VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50),
    shipping_address TEXT,
    contact_phone VARCHAR(20),
    contact_name VARCHAR(50),
    order_status SMALLINT DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_time TIMESTAMP,
    shipping_time TIMESTAMP,
    completion_time TIMESTAMP,
    remark TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 为PostgreSQL添加列注释
COMMENT ON COLUMN orders.order_id IS '订单ID';
COMMENT ON COLUMN orders.user_id IS '用户ID';
COMMENT ON COLUMN orders.order_number IS '订单编号';
COMMENT ON COLUMN orders.total_amount IS '订单总金额';
COMMENT ON COLUMN orders.payment_method IS '支付方式';
COMMENT ON COLUMN orders.shipping_address IS '收货地址';
COMMENT ON COLUMN orders.contact_phone IS '联系电话';
COMMENT ON COLUMN orders.contact_name IS '联系人姓名';
COMMENT ON COLUMN orders.order_status IS '订单状态：0-待付款，1-已付款，2-已发货，3-已完成，4-已取消';
COMMENT ON COLUMN orders.create_time IS '创建时间';
COMMENT ON COLUMN orders.payment_time IS '支付时间';
COMMENT ON COLUMN orders.shipping_time IS '发货时间';
COMMENT ON COLUMN orders.completion_time IS '完成时间';
COMMENT ON COLUMN orders.remark IS '订单备注';

-- 创建订单商品关联表
CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 为PostgreSQL添加列注释
COMMENT ON COLUMN order_items.item_id IS '订单项ID';
COMMENT ON COLUMN order_items.order_id IS '订单ID';
COMMENT ON COLUMN order_items.product_id IS '商品ID';
COMMENT ON COLUMN order_items.quantity IS '购买数量';
COMMENT ON COLUMN order_items.unit_price IS '单价';
COMMENT ON COLUMN order_items.subtotal IS '小计金额';

-- 生成模拟数据
-- 1. 插入用户数据
DO $$
DECLARE
    i INT;
    gender_arr VARCHAR[] := ARRAY['男', '女'];
    provinces VARCHAR[] := ARRAY['北京市', '上海市', '广东省', '江苏省', '浙江省', '四川省', '湖北省', '河南省', '山东省', '福建省'];
    cities VARCHAR[] := ARRAY['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉', '郑州', '济南', '厦门'];
    districts VARCHAR[] := ARRAY['海淀区', '朝阳区', '浦东新区', '天河区', '福田区', '西湖区', '玄武区', '武侯区', '江汉区', '金水区', '历下区', '思明区'];
    streets VARCHAR[] := ARRAY['中关村大街', '建国路', '世纪大道', '天河路', '深南大道', '西湖大道', '中山路', '人民路', '解放路', '和平路'];
    last_names VARCHAR[] := ARRAY['张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴', '郑', '孙', '马', '朱', '胡', '林', '郭', '何', '高', '罗'];
    first_names VARCHAR[] := ARRAY['伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '洋', '艳', '勇', '军', '杰', '娟', '涛', '明', '超', '秀兰', '霞', '平', '刚', '桂英'];
    username_prefix VARCHAR[] := ARRAY['happy', 'cool', 'super', 'fancy', 'lucky', 'smart', 'bright', 'sunny', 'clever', 'great'];
    username_suffix VARCHAR[] := ARRAY['user', 'star', 'fan', 'love', 'joy', 'hero', 'king', 'queen', 'master', 'expert'];
    email_domains VARCHAR[] := ARRAY['qq.com', '163.com', '126.com', 'gmail.com', 'hotmail.com', 'sina.com', 'sohu.com', 'yahoo.com', 'outlook.com'];
    random_username VARCHAR;
    random_email VARCHAR;
    random_phone VARCHAR;
    random_real_name VARCHAR;
    random_gender VARCHAR;
    random_birth_date DATE;
    random_address TEXT;
    random_last_login TIMESTAMP;
BEGIN
    FOR i IN 1..5000 LOOP
        -- 生成随机用户名
        random_username := username_prefix[1 + floor(random() * array_length(username_prefix, 1))] || 
                          username_suffix[1 + floor(random() * array_length(username_suffix, 1))] || 
                          i::VARCHAR;
        
        -- 生成随机邮箱
        random_email := random_username || '@' || email_domains[1 + floor(random() * array_length(email_domains, 1))];
        
        -- 生成随机手机号
        random_phone := '1' || (ARRAY['3', '5', '7', '8', '9'])[1 + floor(random() * 5)] || 
                       lpad(floor(random() * 100000000)::TEXT, 8, '0');
        
        -- 生成随机姓名
        random_real_name := last_names[1 + floor(random() * array_length(last_names, 1))] || 
                           first_names[1 + floor(random() * array_length(first_names, 1))];
        
        -- 生成随机性别
        random_gender := gender_arr[1 + floor(random() * 2)];
        
        -- 生成随机出生日期（1970-2000年之间）
        random_birth_date := '1970-01-01'::DATE + (random() * 365 * 30)::INTEGER;
        
        -- 生成随机地址
        random_address := provinces[1 + floor(random() * array_length(provinces, 1))] || 
                         cities[1 + floor(random() * array_length(cities, 1))] || 
                         districts[1 + floor(random() * array_length(districts, 1))] || 
                         streets[1 + floor(random() * array_length(streets, 1))] || 
                         floor(random() * 100)::TEXT || '号';
        
        -- 生成随机最后登录时间（过去一年内）
        random_last_login := CURRENT_TIMESTAMP - (random() * 365 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second';
        
        -- 插入用户数据
        INSERT INTO users (username, password, email, phone, real_name, gender, birth_date, address, registration_time, last_login_time, status)
        VALUES (
            random_username,
            md5(random()::TEXT), -- 使用MD5生成随机密码
            random_email,
            random_phone,
            random_real_name,
            random_gender,
            random_birth_date,
            random_address,
            CURRENT_TIMESTAMP - (random() * 365 * 3 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second', -- 注册时间在过去三年内
            random_last_login,
            CASE WHEN random() < 0.95 THEN 1 ELSE 0 END -- 95%的用户状态为正常
        );
    END LOOP;
END $$;

-- 2. 插入商品数据
DO $$
DECLARE
    i INT;
    categories VARCHAR[] := ARRAY['手机数码', '电脑办公', '家用电器', '服装鞋帽', '食品生鲜', '美妆护肤', '家居家装', '母婴玩具', '运动户外', '图书音像', '汽车用品', '珠宝首饰'];
    product_prefixes VARCHAR[] := ARRAY['全新', '时尚', '高端', '经典', '豪华', '精品', '优质', '舒适', '轻便', '实用', '智能', '专业', '高效', '便携', '耐用'];
    product_names VARCHAR[] := ARRAY['手机', '笔记本电脑', '平板电脑', '智能手表', '电视机', '冰箱', '洗衣机', '空调', 'T恤', '牛仔裤', '连衣裙', '运动鞋', '休闲鞋', '高跟鞋', '水果礼盒', '坚果零食', '有机蔬菜', '面膜', '洗面奶', '护肤套装', '沙发', '床垫', '餐桌', '婴儿奶粉', '尿不湿', '儿童玩具', '跑步机', '瑜伽垫', '登山包', '小说', '教材', '音乐CD', '汽车座套', '行车记录仪', '机油', '钻石项链', '黄金手镯', '银饰耳环'];
    product_suffixes VARCHAR[] := ARRAY['旗舰版', '豪华版', '至尊版', '限量版', '经典款', '时尚款', '舒适款', '轻薄款', '专业版', '入门版', '高配版', '标准版', '增强版', '尊享版'];
    descriptions VARCHAR[] := ARRAY['这是一款高品质的产品，性价比极高。', '采用顶级材料制作，品质保证。', '设计精美，功能强大，是您的不二之选。', '简约时尚的设计，满足您的日常需求。', '专为追求品质生活的您打造。', '精工细作，注重每一个细节。', '多功能设计，满足您的多样化需求。', '经典款式，永不过时。', '创新科技，引领潮流。', '舒适体验，尽享品质生活。'];
    image_prefixes VARCHAR[] := ARRAY['https://img.example.com/products/', 'https://images.store.cn/items/', 'https://pics.mall.com/goods/', 'https://photos.shop.net/product/'];
    random_product_name VARCHAR;
    random_category VARCHAR;
    random_price DECIMAL;
    random_stock INT;
    random_description TEXT;
    random_image_url VARCHAR;
    random_create_time TIMESTAMP;
    random_update_time TIMESTAMP;
BEGIN
    FOR i IN 1..5000 LOOP
        -- 生成随机商品名称
        random_product_name := product_prefixes[1 + floor(random() * array_length(product_prefixes, 1))] || ' ' || 
                              product_names[1 + floor(random() * array_length(product_names, 1))] || ' ' || 
                              product_suffixes[1 + floor(random() * array_length(product_suffixes, 1))];
        
        -- 生成随机商品类别
        random_category := categories[1 + floor(random() * array_length(categories, 1))];
        
        -- 生成随机价格（10-9999元）
        random_price := 10 + (random() * 9989);
        
        -- 生成随机库存（0-1000）
        random_stock := floor(random() * 1001);
        
        -- 生成随机描述
        random_description := descriptions[1 + floor(random() * array_length(descriptions, 1))] || ' ' || 
                             descriptions[1 + floor(random() * array_length(descriptions, 1))];
        
        -- 生成随机图片URL
        random_image_url := image_prefixes[1 + floor(random() * array_length(image_prefixes, 1))] || i || '.jpg';
        
        -- 生成随机创建时间（过去两年内）
        random_create_time := CURRENT_TIMESTAMP - (random() * 365 * 2 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second';
        
        -- 生成随机更新时间（在创建时间之后）
        random_update_time := random_create_time + (random() * (CURRENT_TIMESTAMP - random_create_time));
        
        -- 插入商品数据
        INSERT INTO products (product_name, category, price, stock, description, image_url, create_time, update_time, status)
        VALUES (
            random_product_name,
            random_category,
            ROUND(random_price::NUMERIC, 2),
            random_stock,
            random_description,
            random_image_url,
            random_create_time,
            random_update_time,
            CASE WHEN random() < 0.9 THEN 1 ELSE 0 END -- 90%的商品状态为上架
        );
    END LOOP;
END $$;

-- 3. 插入订单和订单项数据
DO $$
DECLARE
    i INT;
    j INT;
    random_user_id INT;
    random_order_number VARCHAR;
    random_payment_method VARCHAR;
    random_order_status SMALLINT;
    random_create_time TIMESTAMP;
    random_payment_time TIMESTAMP;
    random_shipping_time TIMESTAMP;
    random_completion_time TIMESTAMP;
    random_remark TEXT;
    current_order_id INT;
    random_product_id INT;
    random_quantity INT;
    random_unit_price DECIMAL;
    random_subtotal DECIMAL;
    order_total_amount DECIMAL;
    user_info RECORD;
    payment_methods VARCHAR[] := ARRAY['支付宝', '微信支付', '银行卡', '货到付款', '信用卡'];
    remarks VARCHAR[] := ARRAY['请尽快发货', '周末送货', '工作日送货', '电话联系', '放到门卫处', '需要发票', '送货上门', '不要打电话', '加急处理', ''];
    max_user_id INT;
    max_product_id INT;
    items_count INT;
BEGIN
    -- 获取最大用户ID和商品ID
    SELECT MAX(user_id) INTO max_user_id FROM users;
    SELECT MAX(product_id) INTO max_product_id FROM products;
    
    FOR i IN 1..1000000 LOOP
        -- 随机选择一个用户
        random_user_id := 1 + floor(random() * max_user_id);
        
        -- 获取用户信息
        SELECT phone, real_name, address INTO user_info FROM users WHERE user_id = random_user_id;
        
        -- 生成随机订单编号
        random_order_number := 'ORD' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || LPAD(i::TEXT, 6, '0');
        
        -- 随机选择支付方式
        random_payment_method := payment_methods[1 + floor(random() * array_length(payment_methods, 1))];
        
        -- 随机选择订单状态（0-4）
        random_order_status := floor(random() * 5);
        
        -- 生成随机创建时间（过去一年内）
        random_create_time := CURRENT_TIMESTAMP - (random() * 365 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second';
        
        -- 根据订单状态生成相应的时间
        IF random_order_status >= 1 THEN
            -- 已付款及以上状态
            random_payment_time := random_create_time + (random() * 24 * 60 * 60)::INTEGER * INTERVAL '1 second';
        ELSE
            random_payment_time := NULL;
        END IF;
        
        IF random_order_status >= 2 THEN
            -- 已发货及以上状态
            random_shipping_time := random_payment_time + (random() * 3 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second';
        ELSE
            random_shipping_time := NULL;
        END IF;
        
        IF random_order_status >= 3 THEN
            -- 已完成状态
            random_completion_time := random_shipping_time + (random() * 7 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second';
        ELSE
            random_completion_time := NULL;
        END IF;
        
        -- 随机选择备注
        random_remark := remarks[1 + floor(random() * array_length(remarks, 1))];
        
        -- 插入订单数据（总金额先设为0，后面计算）
        INSERT INTO orders (user_id, order_number, total_amount, payment_method, shipping_address, contact_phone, contact_name, order_status, create_time, payment_time, shipping_time, completion_time, remark)
        VALUES (
            random_user_id,
            random_order_number,
            0, -- 总金额先设为0
            random_payment_method,
            user_info.address,
            user_info.phone,
            user_info.real_name,
            random_order_status,
            random_create_time,
            random_payment_time,
            random_shipping_time,
            random_completion_time,
            random_remark
        ) RETURNING order_id INTO current_order_id;
        
        -- 为每个订单生成1-5个订单项
        items_count := 1 + floor(random() * 5);
        order_total_amount := 0;
        
        FOR j IN 1..items_count LOOP
            -- 随机选择一个商品
            random_product_id := 1 + floor(random() * max_product_id);
            
            -- 随机选择购买数量（1-10）
            random_quantity := 1 + floor(random() * 10);
            
            -- 获取商品单价
            SELECT price INTO random_unit_price FROM products WHERE product_id = random_product_id;
            
            -- 如果没有找到商品，使用随机价格
            IF random_unit_price IS NULL THEN
                random_unit_price := 10 + (random() * 990);
            END IF;
            
            -- 计算小计金额
            random_subtotal := random_unit_price * random_quantity;
            
            -- 累加总金额
            order_total_amount := order_total_amount + random_subtotal;
            
            -- 插入订单项数据
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
            VALUES (
                current_order_id,
                random_product_id,
                random_quantity,
                ROUND(random_unit_price::NUMERIC, 2),
                ROUND(random_subtotal::NUMERIC, 2)
            );
        END LOOP;
        
        -- 更新订单总金额
        UPDATE orders SET total_amount = ROUND(order_total_amount::NUMERIC, 2) WHERE order_id = current_order_id;
    END LOOP;
END $$;

-- 验证数据
-- 查询用户总数
SELECT COUNT(*) AS user_count FROM users;

-- 查询商品总数
SELECT COUNT(*) AS product_count FROM products;

-- 查询订单总数
SELECT COUNT(*) AS order_count FROM orders;

-- 查询订单项总数
SELECT COUNT(*) AS order_item_count FROM order_items;

-- 查询各订单状态的订单数量
SELECT order_status, COUNT(*) AS count FROM orders GROUP BY order_status ORDER BY order_status;

-- 查询销量前10的商品
SELECT p.product_id, p.product_name, SUM(oi.quantity) AS total_sales
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_sales DESC
LIMIT 10;

-- 查询消费金额前10的用户
SELECT u.user_id, u.username, u.real_name, SUM(o.total_amount) AS total_spent
FROM users u
JOIN orders o ON u.user_id = o.user_id
GROUP BY u.user_id, u.username, u.real_name
ORDER BY total_spent DESC
LIMIT 10;

-- 查询平均订单金额
SELECT AVG(total_amount) AS avg_order_amount FROM orders;

-- 查询各商品类别的销售情况
SELECT p.category, COUNT(DISTINCT o.order_id) AS order_count, SUM(oi.quantity) AS total_quantity, SUM(oi.subtotal) AS total_sales
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.category
ORDER BY total_sales DESC;
