from app import db, socketio
from app.BackgroundThreads import async_apply_and_hire
from app.utils.db_guard import db_call_guard
from classes.Player.index import Player
from bson import ObjectId


class Job:
    def __init__(self, title=None, company=None, id=None):
        self._id = id
        self.title = title
        self.company = company
        self.industry = None
        self.description = None
        self.requirements = []
        self.benefits = []
        self.rate_per_hour = 0
        self.hours_per_mo = 0
        self.available = True
        self.applications = []
        self.staff = []
        self.experience = 0  # Minimum experience required to get this job
        self.experience_point = 0  # experience points earned for this job per month

        # Load from DB by id if provided
        if self._id is not None:
            loaded = self.load_from_db(id=self._id)
            if loaded:
                # Overwrite current attributes with DB data
                self.__dict__.update(loaded.__dict__)
        # Otherwise, try to load by title+company if both provided and id not provided
        elif self.title is not None and self.company is not None:
            loaded = self.load_from_db(title=self.title, company=self.company)
            if loaded:
                self.__dict__.update(loaded.__dict__)

    def set_title(self, title):
        self.title = title

    def set_industry(self, industry):
        self.industry = industry

    def set_company(self, company):
        self.company = company

    def set_description(self, description):
        self.description = description

    def set_requirements(self, requirements):
        if isinstance(requirements, list):
            self.requirements = requirements
        else:
            self.requirements = [requirements]

    def add_requirement(self, requirement):
        self.requirements.append(requirement)

    def set_benefits(self, benefits):
        if isinstance(benefits, list):
            self.benefits = benefits
        else:
            self.benefits = [benefits]

    def set_available(self, is_available=True):
        self.available = is_available

    def set_applications(self, applications):
        self.applications = applications

    def set_staff(self, staff):
        if isinstance(staff, list):
            self.staff = staff
        else:
            self.staff = [staff]

    def add_staff_member(self, player_username):
        if player_username not in self.staff:
            self.staff.append(player_username)

    def add_benefit(self, benefit):
        self.benefits.append(benefit)

    def set_rate_per_hour(self, rate_per_hour):
        self.rate_per_hour = rate_per_hour

    def set_hours_per_month(self, hours):
        self.hours_per_mo = hours

    def set_experience(self, experience):
        self.experience = experience

    def set_experience_point(self, experience_point):
        self.experience_point = experience_point

    @staticmethod
    def _to_object_id(id_value):
        """Convert string id to ObjectId if needed, otherwise return as is."""
        if id_value is None:
            return None
        try:
            if isinstance(id_value, str):
                return ObjectId(id_value)
        except Exception:
            # If id is not a valid ObjectId string, return as is
            pass
        return id_value

    def to_dict(self):
        return {
            "id": str(self._id),
            "title": self.title,
            "industry": self.industry,
            "company": self.company,
            "description": self.description,
            "requirements": self.requirements,
            "benefits": self.benefits,
            "rate_per_hour": self.rate_per_hour,
            "hours_per_mo": self.hours_per_mo,
            "available": self.available,
            "applications": self.applications,
            "staff": self.staff,
            "experience": self.experience,
            "experience_point": self.experience_point,
        }

    def save_to_db(self, username=None):
        """
        Save this job to the job collection in db.
        If a job with the same title and company exists, replace it.
        """
        with db_call_guard("Job.save_to_db"):
            job_collection = db["jobs-collection"]
            result = None

            if username:
                result = job_collection.replace_one({}, self.to_dict(), upsert=True)
            else:
                # SELECT BY ID
                if hasattr(self, "_id") and self._id is not None:
                    object_id = self._to_object_id(self._id)
                    result = job_collection.replace_one(
                        {"_id": object_id}, self.to_dict(), upsert=True
                    )
                else:
                    existing_job = job_collection.find_one(
                        {"title": self.title, "company": self.company}
                    )
                    if existing_job and "_id" in existing_job:
                        self._id = existing_job["_id"]
                        object_id = self._to_object_id(self._id)
                        result = job_collection.replace_one(
                            {"_id": object_id}, self.to_dict(), upsert=True
                        )
                    else:
                        result = job_collection.replace_one(
                            {"title": self.title, "company": self.company},
                            self.to_dict(),
                            upsert=True,
                        )
                        # If a new document was inserted, capture its _id
            if result and hasattr(result, "upserted_id") and result.upserted_id:
                self._id = result.upserted_id

    @classmethod
    def load_from_db(cls, title=None, company=None, id=None):
        print(f"Loading from DB with {id}")
        """
        Load a job by title and company from the db.
        Returns a Job instance if found, else None.
        """
        with db_call_guard("Job.load_from_db"):
            job_collection = db["jobs-collection"]

            if id is not None:
                object_id = cls._to_object_id(id)
                job_data = job_collection.find_one({"_id": object_id})
            else:
                job_data = job_collection.find_one({"title": title, "company": company})

            if job_data:
                job = cls()
                job.set_title(job_data.get("title"))
                job.set_industry(job_data.get("industry"))
                job.set_company(job_data.get("company"))
                job.set_description(job_data.get("description"))
                job.set_requirements(job_data.get("requirements", []))
                job.set_benefits(job_data.get("benefits", []))
                job.set_rate_per_hour(job_data.get("rate_per_hour"))
                job.set_hours_per_month(job_data.get("hours_per_mo"))
                job.set_available(job_data.get("available"))
                job.set_applications(job_data.get("applications", []))
                staff_list = job_data.get("staff", [])
                job.set_staff(staff_list)
                job._id = job_data.get("_id")
                job.experience = job_data.get("experience", 0)
                job.experience_point = job_data.get("experience_point", 0)
                return job
            else:
                return None

    def apply(self, player: "Player"):
        """
        Allows a player apply for this job, accounting for experience requirement.
        """
        if any(app.get("username") == player.username for app in self.applications):
            raise ValueError(
                f"Player '{player.username}' has already applied for this job."
            )

        if player.total_time < self.hours_per_mo:
            raise ValueError(
                f"Player '{player.username}' does not have enough 'work' time to apply for this job."
            )

        player_experience = getattr(player, "experience", 0)
        if player_experience < self.experience:
            raise ValueError(
                f"Player '{player.username}' does not meet the minimum experience requirement ({self.experience}) for this job (player has {player_experience})."
            )

        self.applications.append(
            {
                "username": player.username,
                "experience": player_experience,
                # // Other requirements for this job will be checked and collected from player here
            }
        )

        # Move the hiring logic to a background task and send a socket event when completed
        # Use socketio.start_background_task for better compatibility with eventlet workers
        # This ensures proper async handling with Flask-SocketIO and Gunicorn
        socketio.start_background_task(async_apply_and_hire, self, player)
        self.save_to_db()

    def hire(self, player: "Player"):
        """
        Allows a player to get hired for this job.
        If the player is not already hired, assigns this job to them and saves both to the db.
        Will also add experience to player after being hired.
        """
        if hasattr(player, "is_hired") and player.is_hired():
            raise ValueError("Player is already hired for a job.")
        player.job = self._id
        self.available = False
        # Add player to staff list (by username)
        if hasattr(player, "username") and getattr(player, "username", None):
            if player.username not in self.staff:
                self.staff.append(player.username)

        if player.total_time > self.hours_per_mo:
            player.assign_time_slot("work", self.hours_per_mo)

        if hasattr(player, "save_to_db"):
            player.save_to_db()
        # Remove player's application from the applications list after being hired
        self.applications = [
            a for a in self.applications if a.get("username") != player.username
        ]

        # Add default job-made balancesheet assets/income/expenses for this job if relevant
        if (
            hasattr(player, "balancesheet")
            and hasattr(self, "title")
            and hasattr(self, "rate_per_hour")
            and hasattr(self, "hours_per_mo")
        ):
            # Add salary as predictable income entry
            salary_name = f"Salary: {self.title} at {self.company}"
            try:
                player.balancesheet.add_income(
                    salary_name,
                    self.rate_per_hour * self.hours_per_mo,
                    username=player.username,
                )
                player.save_to_db()
            except Exception:
                # Some balancesheet implementations might already have this entry, ignore in that case
                pass

        self.save_to_db()

        # You could add an application log/history here if needed
        return f"Player {getattr(player, 'username', 'unknown')} has applied and is hired for '{self.title}' at {self.company}."

    def unhire(self, player: "Player"):
        """
        Unhire or remove a staff member (player) from this job.
        Sets player's job to None, removes from staff, and updates both in database.
        """
        username = getattr(player, "username", None)
        if not username:
            raise ValueError("Player must have a username to be un-hired.")

        # unallocate work time
        player.remove_allocated_time("work")
        # Remove player from staff list if present
        if username in self.staff:
            self.staff.remove(username)

        # Remove any job-related income/asset from the player's balancesheet (e.g., salary line for this job)
        if (
            hasattr(player, "balancesheet")
            and hasattr(self, "title")
            and hasattr(self, "company")
        ):
            salary_name = f"Salary: {self.title} at {self.company}"
            try:
                # Remove entire salary line, regardless of amount
                player.balancesheet.remove_income(salary_name, username=player.username)
            except Exception:
                pass

        # If the player currently has this job assigned, reset it
        if hasattr(player, "job") and str(player.job) == str(self._id):
            player.job = None
            if hasattr(player, "save_to_db"):
                player.save_to_db()

        # Optionally, could remove from any application lists
        self.applications = [
            a for a in self.applications if a.get("username") != username
        ]
        self.save_to_db()

        # If job now has no staff, set as available
        if not self.staff:
            self.available = True
        return f"Player {username} has been un-hired from '{self.title}' at {self.company}."
