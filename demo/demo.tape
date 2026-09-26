# Records assets/demo.gif for the README. Run from this directory: vhs demo.tape
# Uses your own Neovim config, with steplink.nvim and fzf-lua installed.

Output ../assets/demo.gif

Set Shell "bash"
Set FontFamily "Iosevka Nerd Font"
Set FontSize 17
Set Width 1200
Set Height 680
Set Padding 16
Set Margin 20
Set MarginFill "#1e2326"
Set WindowBar Colorful
Set BorderRadius 10
Set TypingSpeed 70ms
Set Theme { "name": "Everforest Dark Hard", "background": "#272e33", "foreground": "#d3c6aa", "cursor": "#d3c6aa", "selection": "#374145", "black": "#414b50", "red": "#e67e80", "green": "#a7c080", "yellow": "#dbbc7f", "blue": "#7fbbb3", "magenta": "#d699b6", "cyan": "#83c092", "white": "#d3c6aa", "brightBlack": "#859289", "brightRed": "#e67e80", "brightGreen": "#a7c080", "brightYellow": "#dbbc7f", "brightBlue": "#7fbbb3", "brightMagenta": "#d699b6", "brightCyan": "#83c092", "brightWhite": "#d3c6aa" }

Hide
# Diagnostics off: the demo has no language-server setup, only steplink
Type "nvim -c 'lua vim.diagnostic.enable(false)' garden/features/watering.feature"
Enter
Sleep 2.5s
Show

# 1. A step in a .feature file -> its step definition
Sleep 1s
Type "6G"
Sleep 1s
Type " ss"
Sleep 2.5s

# 2. A step definition -> every scenario that uses it (fzf-lua picker with preview)
Type " ss"
Sleep 3s
Down
Sleep 700ms
Down
Sleep 1.2s
Enter
Sleep 2.5s

# 3. Step definitions no scenario uses
Type ":StepLinkOrphans"
Sleep 600ms
Enter
Sleep 3.5s
