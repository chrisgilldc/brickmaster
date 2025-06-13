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