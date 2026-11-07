# Hands-on test checklist

This is a list of things to click through in a real browser, one at a time, to check the
whole thing works. Each check tells you **what to do** and **what you should see**.

Read the "why this matters" line on the important ones. Those explain what breaks if the
check fails, which is usually more useful than the check itself.

---

## First, get the app running

Open two terminal windows.

In the first one:

```bash
cd backend
pdm run dev
```

In the second one:

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

You will also want this page open in a second tab: **http://127.0.0.1:8000/docs**

That second page is the server's own interface. It lists every piece of data the app can
read or change, and it lets you look at the raw data with your own eyes. When a check says
"check the server directly", it means "use that page". It is the easiest way to catch the
app quietly showing you something different from what was actually saved.

---

## The setup you will type in

You are going to create one trip and three people, and give each person a budget and some
preferences. Do this by hand through the app, because it also tests that adding people works.

**The trip:** name it `E2E`, set *From* to `Toronto`, and set *Days* to `3`.

**The three people:**

| Name | Budget | Travel max | Climates | Activities |
| --- | --- | --- | --- | --- |
| Ada | 500 | 12 | `warm, mild` | `beach, food` |
| Ben | 800 | 20 | `temperate, cold` | `culture, history` |
| Cy | 1200 | 24 | leave this blank | `nightlife, food, shopping` |

**Two limits** (the app calls these "conditions"):

- Ben sets **"No more than $800 pp"**, type `budget`, marked **fixed**
- Ada sets **"Somewhere warm"**, type `climate`, left **flexible**

**Climates and activities are picked, not typed.** In the app they are dropdowns with tick
boxes. Only words that actually exist in the dataset are offered — **seven climates** (`arid`,
`cold`, `continental`, `mild`, `temperate`, `tropical`, `warm`) and **nine activity types**
(`adventure`, `beach`, `culture`, `food`, `history`, `nature`, `nightlife`, `shopping`,
`wellness`). That matters because the scoring compares these words exactly, so a typo or a
made-up word like "sunny" would quietly match nothing.

**Why these exact numbers matter:** the destinations in the dataset cost between about
**$87 and $1089** for three days. So Ada's $500 budget is too small for many of them, Ben's
$800 is too small for some, and Cy's $1200 covers everything. If you use bigger budgets,
everyone will say "All within budget" and you will not be able to test the budget warnings
at all.

---

## Part 1 — The checks that decide whether your study is valid

Do these first. If any of them fail, the comparison between your two interface versions
means nothing, and no amount of polish elsewhere will save it.

### 1. Switching between the two versions must not change the answer

**What to do:** Look at the top five destinations and note their names and their Group
numbers. Now click **Plain**. Look again. Click **Conflict-aware** to switch back.

**What you should see:** In Plain, the four member columns disappear, and so do the
**Friction** and **Disagreement** columns. The legend's third item changes from "conflict"
to "weak fit". But the top five destinations, their Group numbers, and their order must be
**exactly the same** in both versions.

**Why this matters:** the two versions differ only in what they show you. They run the same
calculation. If the ranking changes when you flip the switch, your two groups are not
experiencing the same recommendation, and you cannot compare them.

### 2. The Plain version must genuinely hide the disagreements

**What to do:** While in Plain, click any destination row.

**What you should see:** A panel slides in from the right. It should **not** contain "Fit per
person", it should **not** contain "In the way", and it should **not** contain "Why it sits
here". It **should** still contain "My call", "My limits" and "Approval".

**Why this matters:** if any information about how each person scored leaks into the Plain
version, then Plain is not really the "no conflict support" version, and your comparison is
contaminated.

### 3. The same inputs must always give the same ranking

**What to do:** Reload the page three times. Then change *Acting as* to a different person.
Then change the *Ranking strategy* dropdown to another option and back to the first one.

**What you should see:** The order of destinations and their Group numbers never wobble for
no reason. Same setup always gives the same answer.

### 4. A good score is not the same as everyone agreeing

**What to do:** Open any destination. At the bottom of the panel, switch on the approval
toggle for two of the three people. Then switch on the third, then switch one back off.

**What you should see:** The circle with the count inside updates as you go: 2/3, then 3/3
with the words "Everyone in", then back to 2/3. It should never say everyone is in while
someone is still missing.

**Why this matters:** this is one of the rules of your project. A destination can score
brilliantly and still not be agreed on. The interface must keep those two ideas separate.

### 5. Only the person who set a limit can change it

**What to do:** In the **People** tab, act as Ada and look at Ben's card. His limit should
appear as plain text with no button next to it. Then go to the server page
(**http://127.0.0.1:8000/docs**), find `PATCH /conditions/{condition_id}`, and try to change
that condition's status while claiming to be Ada.

**What you should see:** Ben's card shows his limit as a plain label with no "Mark flexible"
button. When you try the change on the server page while claiming to be Ada, you get an
error saying **403** (which means "not allowed"). When you try the same thing while claiming
to be Ben, it succeeds.

**Why this matters:** your project promises that a fixed limit cannot be moved by anyone
else. If the server allows it, the promise is empty.

### 6. The two votes that look similar but are not

**What to do:** Find a destination. Note its Group number. Open it, click **Skip**, close it,
and look again. Then open it, click **No**, close it, and look again. Then click
**Interested** and look once more.

**What you should see:** After **Skip**, the Group number is **unchanged**. That is
deliberate: skipping a card is not a rejection, it only means the person had no opinion.
After **No**, the number **goes down**. After **Interested**, it goes **up above** where it
started.

### 7. "Interested if…" must create a limit, not just an opinion

**What to do:** Open a destination and click **If…**. A small browser prompt appears asking
what has to be true. Type `only if under $700` and accept it.

**What you should see:** A line appears saying your condition was recorded from that choice.
If you now go to the **People** tab, that sentence shows up under your limits.

**Why this matters:** this is the difference between "I like it" and "I like it on one
condition". The second one has to be remembered as a condition, because it is what the group
will later have to negotiate about.

### 8. A veto beats a good score

**What to do:** Open one of the top-ranked destinations and click **Veto** in the bottom
right of the panel.

**What you should see:** The Group number becomes a dash instead of a number. The row goes
pale, the destination name gets a line through it, and the row drops to the bottom of the
list. The "Choose this" button is no longer clickable. The Veto button has changed into
"Withdraw veto", and clicking that puts everything back.

### 9. Deleting a plan item and relaxing a limit are recorded as different things

**What to do:** First relax one of your own fixed limits (see check 15), then remove one
activity from the plan (see check 17). Now open the **Record** tab.

**What you should see:** Two separate entries. One says "Condition changed" and one says
"Plan changed", and they have differently coloured dots.

**Why this matters:** your project is interested in whether a group settled a disagreement by
changing the trip, or by someone giving way. If the record cannot tell those apart, you
cannot study it.

---

## Part 2 — Everyday use

### 10. Adding people and their preferences

**What to do:** Create the trip, then add Ada, Ben and Cy. Then, for each one, switch
*Acting as* to that person, open the **People** tab, and fill in their budget, travel limit,
climates and activities. The budget and travel boxes save when you click away. The climates
and activities are dropdowns — open one and tick as many as you like; each tick saves straight
away.

**What you should see:** The dropdown shows your chosen words as small green pills inside the
box, and the menu only ever offers words that exist in the dataset. Closing and reopening the
menu keeps your ticks.

Each person gets their own card. The meter on Ada's card should be mostly salmon (because many
destinations are over her $500 budget) and say something like "31 over budget". Cy's should be
green and say "All within budget". Each card lists their wants as small chips and their limits
as tags.

If everyone says "All within budget", your budgets did not save. Try again.

### 11. The comparison table fills up

**What to do:** Open the **Compare** tab.

**What you should see:** 50 rows, one per destination, numbered 1 to 50. Each row shows a
small photo, the destination name, and a line underneath with the climate, the estimated
cost and the flight time from Toronto. The Group numbers must count downwards as you read
down the list. Small bars sit under each person's score.

### 12. Changing how the group is ranked

**What to do:** Use the *Ranking strategy* dropdown in the header. Try **Highest average**,
then **Least-satisfied member**.

**What you should see:** The order visibly changes. A destination that looks fine on average
but leaves one person unhappy will drop when you pick "Least-satisfied member". When you go
back to **Highest average**, the original order returns exactly.

### 13. Reading one destination in detail

**What to do:** Click any row.

**What you should see:** The panel on the right shows, for each person, a coloured bar and
their score out of 100. Below that, a list of any disagreements, then a short paragraph
explaining why the destination sits where it does. Further down are your own vote buttons
and your own limits.

Hover over a person's row and the browser will show you the reason in a tooltip.

### 14. Choosing a destination

**What to do:** In that panel, click **Choose this**.

**What you should see:** The panel closes. If you now open the **Plan** tab, the heading uses
that destination's name.

---

## Part 3 — Awkward situations

### 15. Relaxing your own fixed limit

**What to do:** Switch to being Ben. Open any destination. Under "My limits", his fixed limit
has a small **Relax** button. Click it.

**What you should see:** A pale amber box appears explaining what the change affects, with
**Confirm change** and **Cancel**. If you press Cancel, nothing changes. If you press Confirm,
the limit loses its solid salmon outline, meaning it is no longer fixed, and the **Record**
tab gains a "Condition changed" entry.

### 16. Building the day-by-day plan

**What to do:** With a destination chosen, open the **Plan** tab and click **Build plan**.

**What you should see:** A timetable appears with "Day 1", "Day 2" and "Day 3". Each scheduled
activity shows a start time, a name, its cost, how long it takes, and how long it takes to
get there. Below the timetable is a list of every activity available at that destination
(there should be 12).

If some activities could not be fitted in, a banner at the top names them and says why. There
are three kinds of reason: its opening hours never overlap the day, it does not fit what is
left of the day's budget, or there is no free slot long enough. Those same activities are
marked **not placed** in the list below; hover the label to read the reason.

**Each day has a spending cap.** When your travellers have budgets, the day heading shows
something like "Day 2 · $45 of $267". The cap is the strictest member budget divided evenly
across the days, so the person with the least money sets the pace.

**Build plan** and **Fill gaps** are different. Building throws the timetable away and packs it
again, keeping locked rows where they are. **Fill gaps** leaves everything already on the
timetable exactly where it is and only puts activities into the empty time.

A timetable belongs to one destination. If you change the destination, the timetable is thrown
away and you will see "No plan yet" until you build it again. That is deliberate: a schedule
of Dubrovnik's activities makes no sense once the group has switched to Rio.

### 17. Removing an activity, and being stopped when you should be

**What to do:** On one of the scheduled activities, click **Remove**.

**What you should see:** An amber box appears naming the people affected and what will change.
Press **Cancel** the first time to confirm nothing happens.

Now make the interesting case happen.

Go to **People**, act as Ben, and add a condition. There is a catch worth knowing: the app
decides whether a change "touches" a limit by looking for either the activity's **type** or
its **exact name** inside the condition's text. So the condition has to contain a word that
actually appears in the activity list.

Every row in the timetable, and every activity in the list below it, shows its type in small
grey text just after the name — `culture`, `nature`, `food`, `nightlife`, `shopping` or
`history`. Pick one you can see on screen, and write the condition using that word. For
example, if the activity you are looking at says `culture`, then use the text
`No culture days at all`, type `activity`, marked **fixed**. Then go back to **Plan** and
click **Remove** on an activity of that same type.

**If you specifically want a beach one:** beach is a rare type. Only 15 of the 600 activities
are `beach`, and they only exist at Split, Cancún, Hong Kong, Rio de Janeiro, Lima, Dubrovnik,
Cape Town, Dubai, Kuala Lumpur and San Francisco. At every other destination there are none,
which is why you could not find one.

**What you should see depends on who you are acting as, and this is the interesting part.**

Try it first while acting as **Ada**, who is not the person who set that limit. The **Apply**
button is greyed out, and the box says the change touches a fixed limit set by Ben, and that
only he can confirm it.

Now switch the header dropdown to **Ben** and click **Remove** on the same activity. This time
the button is clickable and reads **Confirm and apply**, with a note saying the limit is his
own so it is his call to make.

That is the rule in plain words: a limit belongs to one person. Nobody else can push a change
through it, and the person who set it can decide to accept the change themselves.

Then remove something nobody has a limit about — for example a `culture` activity when the
only fixed limit is the one about `beach`. Apply is available straight away, the row
disappears from the timetable, and the **Record** tab gains a "Plan changed" entry.

**Worth knowing:** this rule is enforced by the screen, not by the server. Someone determined
could still change the plan through the server page at `/docs`. Making the server itself
refuse is on the list of things still to do.

### 18. Pinning an activity, moving it, and asking for an alternative

**What to do:** Click **Lock** on one of the scheduled activities, then click **Rebuild plan**.

**What you should see:** The locked row stays exactly where it was, on the same day at the
same time. The other activities are re-packed around it and may move. Click **Unlock** and
rebuild again, and that row is free to move like the rest.

**What to do next:** use the small **Day** dropdown on any row to move that activity to a
different day.

**What you should see:** the row jumps to that day, and it is placed after whatever is already
scheduled there. Its start time is set for you.

**Now vote on an activity.** In the list below the timetable, every activity shows a score for
each person and, when they disagree, a red label naming the kind of disagreement. The label can
say **activity** (one person likes this kind of thing and another avoids it), **disagreement**
(their scores are far apart) or **fixed condition** (someone's fixed limit mentions it). Hover
it to read the sentence.

Each activity also has three buttons: **In**, **Out** and **Alt**.

- **In** records that you want it. Your score goes up.
- **Out** records that you don't. Your score goes down, the row is marked "left out", and the
  activity is dropped from the timetable the next time you rebuild the plan.
- **Alt** asks what you would rather do and saves your suggestion.

**What you should see:** click **Out** on a scheduled activity, then **Rebuild plan**, and that
activity is no longer in the timetable. Its row in the list still shows, marked "left out", so
you can see why it went.

Then click **Alt**, type something, and open the **Record** tab. Your suggestion is listed under
"Suggestions", with your name on it.

### 19. Recording the disagreements

**What to do:** Open the **Record** tab and click **Detect conflicts**.

**What you should see:** A list of disagreements appears. Each one shows the people involved
as small circles, a short description, and an orange "open" label. Click **Resolve** next to
one and the label turns green and says "resolved".

### 20. When there is nothing to show

**What to do:** Click **Switch** in the header and create a second trip with no people in it.

**What you should see:** The Compare tab says "No travellers yet" and offers to add one. The
Plan tab says "No destination yet". The People tab says "No travellers yet". Nothing looks
broken or half-drawn.

### 21. When the server is not there

**What to do:** Stop the backend by pressing Control and C in its terminal window. Then
reload the browser page.

**What you should see:** A red box saying it could not refresh, with a **Try again** button.
Start the backend again and press Try again. The app comes back with your data still there.

### 22. When the trip has been deleted

**What to do:** On the server page, find `DELETE /trips/{trip_id}` and delete your trip. Then
reload the browser page.

**What you should see:** You land back on the "Start a trip" screen. The app should not sit
forever on a loading spinner.

---

## Part 4 — Keyboard and small screens

### 23. Using it without a mouse

**What to do:** Press the Tab key repeatedly from the top of the page.

**What you should see:** A dashed outline appears around each thing you can reach, in order:
the tabs, then the dropdowns, then each row of the table. Pressing Enter on a row opens the
detail panel. Pressing Escape closes it.

One known gap: when the panel closes, the keyboard focus does not jump back to the row you
opened it from. You have to start tabbing again. That is a small annoyance, not a fault.

### 24. A narrow window

**What to do:** Make the browser window very narrow, roughly the width of a phone.

**What you should see:** The header wraps onto two lines and the tabs scroll sideways. The
table scrolls sideways rather than squashing its columns into unreadable slivers. The detail
panel takes the full width. Nothing overlaps.

Then zoom the page to 200% and check that no text is cut off.

### 25. Reduced motion

**What to do:** If your system has a "reduce motion" setting, turn it on and reload.

**What you should see:** The detail panel appears instantly instead of sliding in, and the
grey loading placeholders stop shimmering.

---

## Part 5 — Does the data look right?

### 26. Sane numbers

**What to do:** Skim the cost and time lines under the destination names in the Compare tab.

**What you should see:** Costs between roughly **$87** and **$1089**. Flight times between
about **1.7 hours** (New York) and **20.8 hours** (Bali). If the times look like they are
measured from London rather than from Toronto, the dataset was rebuilt with the wrong starting
city.

### 27. Everything is present

**What to do:** Count the rows and glance at the photos.

**What you should see:** Exactly 50 destinations. Every row should show a photograph. A few
photos that fail to load will show a plain grey square instead, which is survivable but worth
noting.

---

## Things that are not finished yet

Do not report these as bugs. They are known and deliberate.

1. **There is no screen for setting up a study session.** You create sessions and tasks on the
   server page (`/docs`), then open the app with `?task=<id>` on the end of the address.
2. **People you add through the app have no "participant" link,** so the questionnaire on the
   Record tab shows a note explaining it cannot save answers, instead of saving them.
3. **The day planner ignores budgets and your limits.** It packs activities by how long they
   take, their opening hours and the travel time between them, and it skips anything anyone
   marked Out. It does not check budgets or conditions.
4. **All 50 destinations are listed at once.** There is no search, filter or paging.
5. **The cost figure is for three days on the ground** and does not include flights. Flight
   time is shown separately, on purpose.
6. **In study mode the Plain / Conflict-aware switch is disabled.** That is intended: the
   switch is set by the study task, so a participant cannot change the condition they are in.

---

## Testing the study setup, end to end

The two interface versions only get locked to a real session when the app is opened with a
task number in the address. Here is how to try that.

1. On the server page, create a session: `POST /sessions` with `{"label": "Test"}`.
2. Create a scenario: `POST /scenarios` with `{"label": "Task 1"}`.
3. Create a task: `POST /tasks` with
   `{"session_id": <id from step 1>, "scenario_id": <id from step 2>, "variant": "comparison", "order_index": 1}`.
   Use `"conflict_aware"` instead of `"comparison"` to get the other version.
4. Link your trip to that task: `PATCH /trips/{trip_id}` with the body
   `{"task_instance_id": <the task id>}`.
5. Open **http://localhost:5173/task/<the task id>**.

**What you should see:** the app works out which trip belongs to that task and opens it, with
the Plain / Conflict-aware switch greyed out and the correct one chosen for you. That single
address is the link you give a participant.

Click a few things, then check `GET /tasks/{id}/events` on the server page: what you did is
listed with who did it and when.

If the person you are acting as has no participant link, the questionnaire explains that it
cannot save. If you want to test saving answers, set the member's `participant_id` first.
