# Brickmaster
## MQTT Use

## Displays

/displays/`id`/status - The status of the display, true or false. True if it's displaying something, false if it's off. 
/displays/`id`/set - Send a JSON dict with the commands to set the display. These are:
    'message' - Set the message on the display. No range checking is done! Make sure it fits in the display.
    'backlight' - A boolean to turn the backlight on or off. This will also set the status on or off, since the display isnt' visible when the backlight is off.
    'clear' - Boolean, clear the display. Default is to always clear, but set clear = false if you don't want it to do so.
        Not clearing can result in characters lingering on the display.
    'off' - Turn off the display. If this is set True, everything else is ignored and the display is turned off.


Advanced Display Options
When using the LCD, you can use advanced display commands. This allows certain display effects to be processed on-board,
rather than sending a barrage of MQTT messages.

### The Message

Messages can be sent to the display with three kinds of formats.

#### Simple

Just send a string. Include any advanced formatting you want, such as a hard return. It will be sent to the display verbating.

```
{
    "message": "Line 1\nLine 2"
}
```

Gets:

```
Line 1
Line 2
```
#### Formatted

Messages have contextual formatting. Currently only `align` is implemented, with options `left`, `center` and `right`, 
which will align the text based on the width of the display.
The message is a list, with each item being a dict, specifying `text` and `align`. If `text` is given without `align` this
will behave the same as a simple message.

```
{
    "message": [
        {"text": "Line 1", "align": "left"},
        {"text": "Line 2", "align": "right"}
    ]
}

```

Set the 'message' key to a list, separating out each line as a separate string.
For example:
`{
"message": [
    "Line 1",
    "Line 2"
    ]
}`
Defines two lines.

Alternately, if using the `rotate` effect (see below), a line can be specified as its own list. IE:
`{
"message": [
    "Line 1",
    [ "Line 2 First", "Line 2 Second" ]
    ]
}`

### Effects

Effects are optional, and are applied separately to one or several target lines. While it's possible to apply effects to
a simple message, generally it's best to apply effects to formatted messages, so each line can be addressed distinctl.

Note that it may be possible to stack effects but that behavior hasn't been fully tested and may have odd effects or 
cause crashes.

Effects are defined in the `effects` key of the message body, like so:

```
{
"message": [
    "Line 1",
    "Line 2"
    ],
"effects": {
    "horizontal-scroll": ...
    "rotate": ...
    "vertical-scroll": ...
}
```

#### Horizontal Scroll
Scrolls text left or right along a line. This may blur the text, depending on your display and the speed.
A list may be used to define multiple different effects for different lines.
Options are:
* target - Line or lines to scroll. Remember, lines are zero-indexed from the top of the display. A single line may be 
an integer, otherwise should be a list.
* direction - Either 'left' or 'right', for the direction of the test movement. Defaults to left.
* speed - How fast to move the text. Will move one character in the chosen direction ever "speed" seconds. May decimal 
fractions (ie: 0.1)

Example - 
```
{
"message": [
    "This is a very very long line.",
    "This is an exceedingly long line."
    ],
"effects": {
    "horizontal-scroll": [
        {"target": 0, speed: 1},
        {"target": 1, speed: 0.5, direction: "right"
    ]
}
```

This effect will scroll the first line of text one character to the left every second, and the second line
to the right every half second.

#### Rotate
Rotates among text strings. This is a complete replacement. It's assumed the text will fit in the display.
Options are:
* target - Line or lines to scroll. Remember, lines are zero-indexed from the top of the display. A single line may be 
an integer, otherwise should be a list.
* speed - How fast to move the text. Will move one character in the chosen direction ever "speed" seconds. May decimal 
fractions (ie: 0.1)

Example - 
```
{
"message": [
    "Static Line",
    ["Show This First", "Show This Second"]
    ],
"effects": {
    "rotate": [
        {"target": 1, speed: 1}
    ]
}
```
This effect will swap the second line of the display between the two different values every second.

#### Vertical Scroll
Move lines of text up and down the display.
NOT YET IMPLEMENTED