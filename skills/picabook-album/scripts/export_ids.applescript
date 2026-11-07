on run argv
	set idFile to item 1 of argv
	set outDir to item 2 of argv
	set ids to paragraphs of (read POSIX file idFile as «class utf8»)
	set itemsList to {}
	with timeout of 3000 seconds
	tell application "Photos"
		repeat with i in ids
			if (length of i) > 0 then set end of itemsList to media item id i
		end repeat
		export itemsList to (POSIX file outDir as alias) without using originals
	end tell
	end timeout
	return (count of itemsList) as text
end run
