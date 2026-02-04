# Features

## 1. Personal Features

### 1.1 Workout Management
1. **Upload/Import**: Upload from device by API or import workouts from third-party services
2. **View Workouts**: View other users' workouts (respecting privacy settings)
3. **Social Features**: Follow other users

### 1.2 Privacy Settings
*From features 1.1.2 and 1.1.3, users must be able to configure:*
1. **Private (Default)**: Hide workouts from other users
2. **Followers Only**: Make workouts visible only to followers
3. **Public**: Make workouts visible to everyone

### 1.3 Clubs
1. **Create Clubs**: Ability to create clubs (public or by request)
2. **Membership**:
   1. Ability to join a club (instant for public, request for by_request)
   2. Ability to leave a club
3. **Club Roles**: Owner, Coach, Member

---

## 2. Community Features

### 2.1 Event Management
1. **Create Events**: Users can create/organize events
2. **Event Requirements**:
   1. Consists of one or multiple competitions
   2. Can be open or closed format
   3. Organizer can approve/reject participation requests

### 2.2 Event Participation
Users can participate in events as:

**Team roles:**
1. **Organizer** - Creates and manages the event, full control
2. **Secretary** - Manages registrations, approves athletes, uploads results
3. **Judge** - Officiates competitions, manages results, marks DSQ/DNF
4. **Volunteer** - View-only access to event data, helps with event

**Athlete/Viewer roles:**
5. **Participant** - Competes in competitions
   * Auto-approved for public events, requires approval for by_request events
6. **Spectator** - View-only access to results and live tracking

### 2.3 Competition Details
1. **Multiple Competitions**: Users can choose specific competitions within an event (default: all competitions)
2. **Class Selection**: Users select their competition class (age/gender group)
3. **Workout Linking**: Ability to link recorded workouts to competition participation
4. **Results**: Events and competitions calculate and store results with rankings

---

## 3. Authentication

### 3.1 Auth Methods (MVP)
1. **Username + Password**: Primary authentication
2. **OAuth** (Future): Google, Strava integration

### 3.2 Account Features
1. Password reset
2. Session management (JWT tokens)
