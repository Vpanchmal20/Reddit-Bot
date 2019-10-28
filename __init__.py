import praw, pprint
import isodate
from oauth2client.tools import argparser, run_flow
from db import get_db
from youtube import youTubeInfo
from praw_auth import reddit_auth


connect, youtubeObj, args, youtube = get_db(), youTubeInfo(), argparser.parse_args(), youtubeObj.get_authenticated_service(args)

def main():
	reddit = reddit_auth()
	subReddit = reddit.subreddit('all')
	for comment in subReddit.stream.comments():
		processComments(comment)	

def blacklistUsers(comment):
	comment_text = comment.body.lower()

	if comment_text == 'stop':
		parent = comment.parent()

		if parent.author != 'video_descriptionbot':
			return

		with connect.cursor() as cursor:
			try:
				cursor.execute('INSERT INTO blacklist VALUES("%s")' % (comment.author))
				connect.commit()
			except pymysql.err.IntegrityError as e:
				print(e)

def processComments(comment):
	print(comment)
	blacklistUsers(comment)

	if comment.author == 'video_descriptionbot':
		return

	if 'bot' in str(comment.author):
		return

	if comment.score < 1:
		return

	if 'youtube.com/watch' in comment.body or 'youtu.be' in comment.body:
		with connect.cursor() as cursor:
			cursor.execute('SELECT * FROM  blacklist WHERE author = "%s"' % (comment.author))
			result_blacklist = cursor.rowcount

		if result_blacklist == 1:
			print('User has opted out')
			return

		with connect.cursor() as cursor:
			cursor.execute('SELECT * FROM  comments WHERE comment_id = "%s"' % (comment.id))
			result = cursor.rowcount

		if result == 1:
			return

		words = comment.body.split()
		replyPost = ""

		for word in words:
			if 'youtube.com/watch' in word or 'youtu.be' in word:
				if '](' in word:
					comment_parts = word.split(']')
					youtube_link = comment_parts[1].split(')')[0][1:]
					if create_reply(youtube_link) != False:
						replyPost += create_reply(youtube_link)
				else:
					if create_reply(word) != False:
						replyPost += create_reply(word)

		if replyPost == "":
			return

		replyPost += '\n \n \n \n'+ '****' + '\n \n' + '^(I am a bot, this is an auto-generated reply | )'
		replyPost += '^[Info](https://www.reddit.com/u/video_descriptionbot) ^| '
		replyPost += '^[Feedback](https://www.reddit.com/message/compose/?to=video_descriptionbot&subject=Feedback) ^| '
		replyPost += '^(Reply STOP to opt out permanently)'

		try:
			comment.reply(replyPost)
			print('Successfully replied')
			with connect.cursor() as cursor:
				cursor.execute('INSERT INTO comments VALUES("%s")' % (comment.id))
				connect.commit()

		except Exception as e:
			print (e)

def create_reply(body):
	reply = 'SECTION | CONTENT' +'\n' + ':--|:--' +'\n'

	try:
		if find_id(body) != False:
			replyTitle, replyDescription, replyDuration = find_id(body)
			reply += 'Title | '+ replyTitle +'\n'

			if len(replyDescription) > 1:
				reply += 'Description | '+ replyDescription +'\n'

			reply += 'Length | '+ str(replyDuration) +'\n'
			reply += '\n \n'

			return reply
		else:
			return False

	except TypeError as e:
		print(e)
		return False

def find_id(link):
	if 'v=' in link:
		linkParts = link.split('v=')
		videoID = linkParts[1].split('&')[0]
	elif 'tu.be' in link:
		linkParts = link.split('tu.be/')
		if '?' in linkParts[1]:
			videoID = linkParts[1].split('?')[0]
		else:
			videoID = linkParts[1]

	try:
		results = youtubeObj.list_videos(youtube,videoID)

		for item in results['items']:

			if len(item['snippet']['description']) > 500 :
				description = item['snippet']['description'].replace('\n',' ')[:500]
				description += '...'
			else:
				description = item['snippet']['description'].replace('\n',' ')

			title = item['snippet']['title']
			length = isodate.parse_duration(item['contentDetails']['duration'])

		return title, description, length

	except (UnboundLocalError,TypeError) as e:
		print(e)
		return False

if __name__ == '__main__':
	main()