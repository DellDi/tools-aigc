# -*- coding: utf-8 -*-
import requests
import random
import time
import json
# 载入环境变量
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv('QWEN_API_KEY')

def ask_gpt(msg, system=''''''):
	headers = {
		'Authorization': f'Bearer {QWEN_API_KEY}',
		'Content-Type': 'application/json',
		'X-DashScope-SSE': 'enable',
	}

	json_data = {
		'model': 'qwen-max-latest',
		'input': {
			'messages': [
				{
					'role': 'system',
					'content': system,
				},
				{
					'role': 'user',
					'content': str(msg),
				},
			],
		},
		'parameters': {},
	}
	print(json_data['input']['messages'][1]['content'])
	for i in range(3):
		try:
			response = requests.post(
				'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
				headers=headers,
				json=json_data,
				stream=True
			)
			tmp = ''
			print('AI：', end='')
			for i in response.iter_lines(chunk_size=1000):
				if i.decode('utf8').startswith('data:'):
					txt = json.loads(i.decode('utf8')[5:])['output']['text']
					new_txt = txt.replace(tmp, '')
					for i in new_txt:
						print(i, end='', flush=True)
						# yield i.replace('\n', '<br>')
						time.sleep(0.03)
					tmp = txt
			print()
			return tmp
		except:
			continue


import pygame
import time
import random

# 初始化pygame
pygame.init()

# 定义颜色
白色 = (255, 255, 255)
黄色 = (255, 255, 102)
黑色 = (0, 0, 0)
红色 = (213, 50, 80)
绿色 = (0, 255, 0)
蓝色 = (50, 153, 213)

# 定义屏幕尺寸
屏幕宽度 = 500
屏幕高度 = 300

# 创建游戏窗口
游戏窗口 = pygame.display.set_mode((屏幕宽度, 屏幕高度))
pygame.display.set_caption('贪吃蛇游戏')

# 定义时钟
时钟 = pygame.time.Clock()

# 定义蛇的块大小和速度
蛇块大小 = 10
蛇的速度 = 30

# 新增：自动玩参数和速度倍数
自动玩 = False
速度倍数 = 30

# 新增：自动重新开始变量
自动重新开始 = True

# 加载支持中文的字体
字体样式 = pygame.font.Font(None, 25)
得分字体 = pygame.font.Font(None, 35)

# 显示消息（修改为支持中文）
def 消息(消息内容, 颜色):
    消息对象 = 字体样式.render(消息内容, True, 颜色)
    游戏窗口.blit(消息对象, [屏幕宽度 / 6, 屏幕高度 / 3])

# 新增：显示得分函数
def 显示得分(得分):
    得分对象 = 得分字体.render("你的得分: " + str(得分), True, 黄色)
    游戏窗口.blit(得分对象, [0, 0])

# 新增：绘制蛇的函数
def 绘制蛇(蛇块大小, 蛇列表):
    for 坐标 in 蛇列表:
        pygame.draw.rect(游戏窗口, 黑色, [坐标[0], 坐标[1], 蛇块大小, 蛇块大小])

# 新增：绘制按钮函数
def 绘制按钮(文本, x, y, 宽度, 高度, 颜色):
    pygame.draw.rect(游戏窗口, 颜色, [x, y, 宽度, 高度])
    消息对象 = 字体样式.render(文本, True, 黑色)
    游戏窗口.blit(消息对象, [x + 10, y + 10])

# 新增：检查按钮点击事件
def 检查按钮点击(位置, x, y, 宽度, 高度):
    return x <= 位置[0] <= x + 宽度 and y <= 位置[1] <= y + 高度

# 新增：智能移动函数（进一步优化版）
def 智能移动(蛇头, 食物位置, 当前方向, 蛇列表):
    x差 = 食物位置[0] - 蛇头[0]
    y差 = 食物位置[1] - 蛇头[1]

    # 根据食物位置决定优先移动方向
    if abs(x差) > abs(y差):
        if x差 > 0 and 当前方向 != "左" and 蛇头[0] + 蛇块大小 < 屏幕宽度 and [蛇头[0] + 蛇块大小, 蛇头[1]] not in 蛇列表:
            return "右"
        elif x差 < 0 and 当前方向 != "右" and 蛇头[0] - 蛇块大小 >= 0 and [蛇头[0] - 蛇块大小, 蛇头[1]] not in 蛇列表:
            return "左"
    else:
        if y差 > 0 and 当前方向 != "上" and 蛇头[1] + 蛇块大小 < 屏幕高度 and [蛇头[0], 蛇头[1] + 蛇块大小] not in 蛇列表:
            return "下"
        elif y差 < 0 and 当前方向 != "下" and 蛇头[1] - 蛇块大小 >= 0 and [蛇头[0], 蛇头[1] - 蛇块大小] not in 蛇列表:
            return "上"

    # 如果无法直接移动，则尝试远离墙壁和自身
    if 当前方向 == "右":
        if 蛇头[0] + 蛇块大小 < 屏幕宽度 and [蛇头[0] + 蛇块大小, 蛇头[1]] not in 蛇列表:
            return "右"
        elif 蛇头[1] - 蛇块大小 >= 0 and [蛇头[0], 蛇头[1] - 蛇块大小] not in 蛇列表:  # 尝试向上移动
            return "上"
        elif 蛇头[1] + 蛇块大小 < 屏幕高度 and [蛇头[0], 蛇头[1] + 蛇块大小] not in 蛇列表:  # 尝试向下移动
            return "下"
    elif 当前方向 == "左":
        if 蛇头[0] - 蛇块大小 >= 0 and [蛇头[0] - 蛇块大小, 蛇头[1]] not in 蛇列表:
            return "左"
        elif 蛇头[1] - 蛇块大小 >= 0 and [蛇头[0], 蛇头[1] - 蛇块大小] not in 蛇列表:  # 尝试向上移动
            return "上"
        elif 蛇头[1] + 蛇块大小 < 屏幕高度 and [蛇头[0], 蛇头[1] + 蛇块大小] not in 蛇列表:  # 尝试向下移动
            return "下"
    elif 当前方向 == "下":
        if 蛇头[1] + 蛇块大小 < 屏幕高度 and [蛇头[0], 蛇头[1] + 蛇块大小] not in 蛇列表:
            return "下"
        elif 蛇头[0] - 蛇块大小 >= 0 and [蛇头[0] - 蛇块大小, 蛇头[1]] not in 蛇列表:  # 尝试向左移动
            return "左"
        elif 蛇头[0] + 蛇块大小 < 屏幕宽度 and [蛇头[0] + 蛇块大小, 蛇头[1]] not in 蛇列表:  # 尝试向右移动
            return "右"
    elif 当前方向 == "上":
        if 蛇头[1] - 蛇块大小 >= 0 and [蛇头[0], 蛇头[1] - 蛇块大小] not in 蛇列表:
            return "上"
        elif 蛇头[0] - 蛇块大小 >= 0 and [蛇头[0] - 蛇块大小, 蛇头[1]] not in 蛇列表:  # 尝试向左移动
            return "左"
        elif 蛇头[0] + 蛇块大小 < 屏幕宽度 and [蛇头[0] + 蛇块大小, 蛇头[1]] not in 蛇列表:  # 尝试向右移动
            return "右"

    return 当前方向

# 新增：将游戏状态转换为文本表示的函数
def 游戏状态转文本(蛇列表, 食物x, 食物y, 屏幕宽度, 屏幕高度, 蛇块大小):
	# 创建一个空白棋盘
	棋盘 = [['*' for _ in range(int(屏幕宽度/蛇块大小))] for _ in range(int(屏幕高度/蛇块大小))]
	
	# 标记食物位置
	食物格x = int(食物x/蛇块大小)
	食物格y = int(食物y/蛇块大小)
	棋盘[食物格y][食物格x] = 'F'
	
	# 标记蛇的位置
	for i, 部分 in enumerate(蛇列表):
		x格 = int(部分[0]/蛇块大小)
		y格 = int(部分[1]/蛇块大小)
		if i == len(蛇列表) - 1:  # 蛇头
			棋盘[y格][x格] = 'H'
		else:  # 蛇身
			棋盘[y格][x格] = 'B'
	
	# 转换为字符串
	return '\n'.join([''.join(行) for 行 in 棋盘])

# GPT系统提示词
GPT系统提示词 = '''你是一个贪吃蛇AI控制器。你将收到当前游戏状态的文本表示：
- 'H' 表示蛇头
- 'B' 表示蛇身
- 'F' 表示食物
- '*' 表示空白区域

请分析当前局面并返回下一步移动方向。返回格式必须是以下一个字，禁止输出其他内容或者多余字符：
上/下/左/右

在决策时请考虑：
1. 避免撞墙
2. 避免撞到自己
3. 仔细思考，选择最短路径朝食物方向移动并穿过它，H到达F边上后继续朝F移动
4. 在无法直接到达食物时，选择安全的移动方向
5. H禁止朝B方向移动，例如左边为H右边为B，禁止返回右，其余也同理'''

# 新增：通过GPT获取移动方向
def 获取GPT移动方向(游戏状态):
	try:
		gpt响应 = ask_gpt(游戏状态, GPT系统提示词)
		# 移动指令 = json.loads(gpt响应)
		return gpt响应
	except:
		return None

# 游戏主循环（进一步优化版）
def 游戏主循环():
	global 自动玩, 自动重新开始

	# 新增：模式选择界面
	模式已选择 = False
	while not 模式已选择:
		游戏窗口.fill(蓝色)
		绘制按钮("手动玩", 250, 250, 100, 50, 绿色)
		绘制按钮("GPT玩", 450, 250, 100, 50, 红色)  # 修改按钮文字
		pygame.display.update()

		for 事件 in pygame.event.get():
			if 事件.type == pygame.QUIT:
				pygame.quit()
				quit()
			if 事件.type == pygame.MOUSEBUTTONDOWN:
				鼠标位置 = pygame.mouse.get_pos()
				if 检查按钮点击(鼠标位置, 250, 250, 100, 50):
					自动玩 = False
					模式已选择 = True
				elif 检查按钮点击(鼠标位置, 450, 250, 100, 50):
					自动玩 = True
					print("已选择GPT控制模式！")
					模式已选择 = True

	游戏结束 = False
	游戏关闭 = False

	x1 = 屏幕宽度 / 2
	y1 = 屏幕高度 / 2

	x1变化 = 0
	y1变化 = 0

	蛇列表 = []
	蛇长度 = 1

	食物x = round(random.randrange(0, 屏幕宽度 - 蛇块大小) / 10.0) * 10.0
	食物y = round(random.randrange(0, 屏幕高度 - 蛇块大小) / 10.0) * 10.0

	当前方向 = "右"  # 新增：记录当前方向

	# 新增：未吃到食物的移动计数器
	未吃到计数 = 0
	最大未吃到计数 = 100  # 允许的最大未吃到食物移动次数

	while not 游戏结束:

		while 游戏关闭 == True:
			游戏窗口.fill(蓝色)
			消息("你输了! 按Q退出或C重新开始", 红色)
			显示得分(蛇长度 - 1)
			pygame.display.update()

			for 事件 in pygame.event.get():
				if 事件.type == pygame.KEYDOWN:
					if 事件.key == pygame.K_q:
						pygame.quit()
						quit()
					if 事件.key == pygame.K_c:
						# 重置游戏状态
						x1 = 屏幕宽度 / 2
						y1 = 屏幕高度 / 2
						x1变化 = 0
						y1变化 = 0
						蛇列表 = []
						蛇长度 = 1
						食物x = round(random.randrange(0, 屏幕宽度 - 蛇块大小) / 10.0) * 10.0
						食物y = round(random.randrange(0, 屏幕高度 - 蛇块大小) / 10.0) * 10.0
						游戏关闭 = False

			# 新增：自动重新开始逻辑
			if 自动重新开始:
				# 重置游戏状态
				x1 = 屏幕宽度 / 2
				y1 = 屏幕高度 / 2
				x1变化 = 0
				y1变化 = 0
				蛇列表 = []
				蛇长度 = 1
				食物x = round(random.randrange(0, 屏幕宽度 - 蛇块大小) / 10.0) * 10.0
				食物y = round(random.randrange(0, 屏幕高度 - 蛇块大小) / 10.0) * 10.0
				游戏关闭 = False
				break

		# 修改：处理窗口关闭事件
		for 事件 in pygame.event.get():
			if 事件.type == pygame.QUIT:
				# 直接退出游戏
				pygame.quit()
				quit()
			if 事件.type == pygame.KEYDOWN and not 自动玩:
				if 事件.key == pygame.K_LEFT:
					x1变化 = -蛇块大小
					y1变化 = 0
				elif 事件.key == pygame.K_RIGHT:
					x1变化 = 蛇块大小
					y1变化 = 0
				elif 事件.key == pygame.K_UP:
					y1变化 = -蛇块大小
					x1变化 = 0
				elif 事件.key == pygame.K_DOWN:
					y1变化 = 蛇块大小
					x1变化 = 0

		if x1 >= 屏幕宽度 or x1 < 0 or y1 >= 屏幕高度 or y1 < 0:
			游戏关闭 = True
		x1 += x1变化
		y1 += y1变化
		游戏窗口.fill(蓝色)
		pygame.draw.rect(游戏窗口, 绿色, [食物x, 食物y, 蛇块大小, 蛇块大小])
		蛇头 = []
		蛇头.append(x1)
		蛇头.append(y1)
		蛇列表.append(蛇头)
		if len(蛇列表) > 蛇长度:
			del 蛇列表[0]

		for 坐标 in 蛇列表[:-1]:
			if 坐标 == 蛇头:
				游戏关闭 = True

		绘制蛇(蛇块大小, 蛇列表)
		显示得分(蛇长度 - 1)  # 调用显示得分函数

		pygame.display.update()

		if x1 == 食物x and y1 == 食物y:
			食物x = round(random.randrange(0, 屏幕宽度 - 蛇块大小) / 10.0) * 10.0
			食物y = round(random.randrange(0, 屏幕高度 - 蛇块大小) / 10.0) * 10.0
			蛇长度 += 1
			未吃到计数 = 0  # 重置未吃到计数器
		else:
			未吃到计数 += 1  # 增加未吃到计数

		# 新增：随机扰动机制（进一步优化）
		if 自动玩 and 未吃到计数 > 最大未吃到计数 // 2:  # 减少随机扰动的频率
			可选方向 = ["上", "下", "左", "右"]
			随机方向 = random.choice(可选方向)
			while 随机方向 == 当前方向 or (随机方向 == "上" and y1 - 蛇块大小 < 0) or \
				  (随机方向 == "下" and y1 + 蛇块大小 >= 屏幕高度) or \
				  (随机方向 == "左" and x1 - 蛇块大小 < 0) or \
				  (随机方向 == "右" and x1 + 蛇块大小 >= 屏幕宽度) or \
				  ([x1 + (蛇块大小 if 随机方向 == "右" else -蛇块大小 if 随机方向 == "左" else 0),
					y1 + (蛇块大小 if 随机方向 == "下" else -蛇块大小 if 随机方向 == "上" else 0)] in 蛇列表):
				随机方向 = random.choice(可选方向)

			if 随机方向 == "右":
				x1变化 = 蛇块大小
				y1变化 = 0
			elif 随机方向 == "左":
				x1变化 = -蛇块大小
				y1变化 = 0
			elif 随机方向 == "下":
				y1变化 = 蛇块大小
				x1变化 = 0
			elif 随机方向 == "上":
				y1变化 = -蛇块大小
				x1变化 = 0
			当前方向 = 随机方向
			未吃到计数 = 0  # 重置未吃到计数器

		if 自动玩:
			# 获取当前游戏状态的文本表示
			当前状态 = 游戏状态转文本(蛇列表, 食物x, 食物y, 屏幕宽度, 屏幕高度, 蛇块大小)
			# 获取GPT的移动决策
			gpt方向 = 获取GPT移动方向(当前状态)
			
			if gpt方向:
				if gpt方向 == "右":
					x1变化 = 蛇块大小
					y1变化 = 0
				elif gpt方向 == "左":
					x1变化 = -蛇块大小
					y1变化 = 0
				elif gpt方向 == "下":
					y1变化 = 蛇块大小
					x1变化 = 0
				elif gpt方向 == "上":
					y1变化 = -蛇块大小
					x1变化 = 0
				当前方向 = gpt方向

		# 自动玩模式下的速度调整（降低速度倍数）
		当前速度 = 蛇的速度 * 速度倍数 if 自动玩 else 蛇的速度
		时钟.tick(当前速度)

	pygame.quit()
	quit()

# 启动游戏
游戏主循环()
