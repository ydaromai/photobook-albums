on run argv
	set albumName to item 1 of argv
	set out to ""
	tell application "Photos"
		set a to first album whose name is albumName
		set its_items to media items of a
		repeat with m in its_items
			set d to date of m
			set loc to location of m
			set la to ""
			set lo to ""
			try
				set la to (item 1 of loc) as text
				set lo to (item 2 of loc) as text
			end try
			set out to out & (id of m) & tab & (filename of m) & tab & ((year of d) as text) & "-" & ((month of d as integer) as text) & "-" & ((day of d) as text) & " " & ((time of d) as text) & tab & la & tab & lo & tab & (width of m) & tab & (height of m) & linefeed
		end repeat
	end tell
	return out
end run
