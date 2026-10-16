// Story Dice: nine categories on ten dice. Roll them all and read:
//
//   In [Setting], a [Character] with an [Object] must [Action],
//   but faces [Conflict], feeling [Emotion], because they want [Want],
//   until [Twist], and it ends [Resolution].
//
// Open in OpenSCAD, pick a die in the Customizer, render (F6), export STL.
// To build every die at once: tools/build.sh
//
// Change a face by editing its [icon, label] pair below. Icons are Phosphor
// Fill names (https://phosphoricons.com); drop the SVG into ../icons first.

die = "setting"; // [setting, character, object, action, conflict_a, conflict_b, emotion, want, twist, resolution]
variant = "labelled"; // [labelled, icons]
part = "body"; // [body, ink]
font = "Liberation Sans:style=Bold";

// Used by tools/build.sh --png: colour the already-built STLs instead of
// recomputing them, which gives clean previews. Leave false.
from_stl = false;

include <story_die.scad>

// [die, shape, [body colour, ink colour], [[icon, label], ...]]
// Face order follows shapes.scad. Colours are the suggested filament and paint;
// they show in previews only.
KIT = [
  ["setting", "d8", ["#2FA463", "#F5F2EC"], [
    ["buildings", "CITY"], ["church", "TOWN"], ["mountains", "WILD"], ["road-horizon", "ROAD"],
    ["house", "HOME"], ["bank", "CIVIC"], ["tent", "CAMP"], ["planet", "VOID"]]],
  ["character", "d8", ["#2E74E0", "#F5F2EC"], [
    ["crown", "HERO"], ["compass", "MENTOR"], ["shield", "GUARD"], ["megaphone", "HERALD"],
    ["mask-happy", "SHIFTER"], ["ghost", "SHADOW"], ["handshake", "ALLY"], ["spiral", "TRICK"]]],
  ["object", "d6", ["#E8B300", "#1A1A1A"], [
    ["key", "SECRET"], ["book-open", "LORE"], ["magnifying-glass", "CLUE"],
    ["envelope", "NOTE"], ["flask", "BREW"], ["coins", "GOLD"]]],
  ["action", "d6", ["#F2711C", "#F5F2EC"], [
    ["person-simple-run", "FLEE"], ["eye", "WATCH"], ["hand", "TAKE"],
    ["chats", "SPEAK"], ["airplane-tilt", "FLY"], ["fire", "BURN"]]],
  ["conflict_a", "tt", ["#2B2B2B", "#F5F2EC"], [
    ["brain", "SELF"], ["sword", "RIVAL"], ["bank", "STATE"], ["tree", "NATURE"]]],
  ["conflict_b", "tt", ["#2B2B2B", "#F5F2EC"], [
    ["hourglass", "FATE"], ["robot", "TECH"], ["ghost", "SPIRIT"], ["tornado", "CHAOS"]]],
  ["emotion", "d12", ["#E23B3B", "#F5F2EC"], [
    ["smiley", "JOY"], ["smiley-sad", "GRIEF"], ["heart", "LOVE"], ["lightning", "FEAR"],
    ["star", "HOPE"], ["moon", "DREAM"], ["fire", "RAGE"], ["sun", "WARMTH"],
    ["cloud-rain", "DREAD"], ["smiley-meh", "NUMB"], ["sparkle", "AWE"], ["question", "DOUBT"]]],
  ["want", "d10", ["#DB2777", "#F5F2EC"], [
    ["heartbeat", "SURVIVE"], ["heart", "LOVE"], ["hand-fist", "POWER"], ["bird", "FREEDOM"],
    ["scales", "JUSTICE"], ["knife", "REVENGE"], ["handshake", "BELONG"], ["sun", "REDEEM"],
    ["crown", "RENOWN"], ["lightbulb", "TRUTH"]]],
  ["twist", "d8", ["#7A3FE0", "#F5F2EC"], [
    ["arrows-clockwise", "REVERSE"], ["mask-happy", "UNMASK"], ["knife", "BETRAY"], ["eye", "REVEAL"],
    ["skull", "DEATH"], ["swap", "DOUBLE"], ["door-open", "ARRIVAL"], ["spiral", "UNRAVEL"]]],
  ["resolution", "d6", ["#EDEBE6", "#1A1A1A"], [
    ["sun", "HAPPY"], ["cloud-rain", "TRAGIC"], ["smiley-meh", "BITTER"],
    ["question", "UNKNOWN"], ["infinity", "CIRCLE"], ["dots-three", "CLIFF"]]],
];

function kit_entry(name) =
  let (hit = [for (i = [0:len(KIT) - 1]) if (KIT[i][0] == name) i])
  assert(len(hit) == 1, str("unknown die: ", name))
  KIT[hit[0]];

E = kit_entry(die);
if (from_stl) {
  color(E[2][0]) import(str("../out/stl/", variant, "/", die, ".stl"));
  color(E[2][1]) import(str("../out/stl/", variant, "/", die, "_ink.stl"));
} else {
  story_die(E[1], [for (f = E[3]) f[0]], [for (f = E[3]) f[1]],
            labelled = (variant == "labelled"), part = part, font = font, colors = E[2]);
}
