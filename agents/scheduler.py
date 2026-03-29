import threading
import time

scheduled_posts = []

class SocialScheduler:
    def __init__(self):
        pass

    def schedule_post(self, job_id: str, platform: str, post_time: str, note: str, blog_data: dict, social_data: dict):
        """
        Schedules or posts immediately depending on post_time.
        post_time is 'Now' or a datetime-local string 
        """
        title = blog_data.get("title") or blog_data.get("topic") or "Untitled"
        post_info = {
            "job_id": job_id,
            "platform": platform,
            "note": note,
            "title": title,
            "status": "scheduled",
            "time": post_time
        }
        
        if post_time == "Now":
            post_info["status"] = "sent"
            self._execute_post(platform, social_data)
            scheduled_posts.append(post_info)
            return {"status": "success", "message": f"Posted to {platform} successfully!"}
        
        else:
            scheduled_posts.append(post_info)
            
            # Fire and forget a thread that waits a few secs and marks as sent 
            # (to simulate background worker picking it up)
            def mock_delay():
                time.sleep(8) # Mock delay for demonstration
                post_info["status"] = "sent"
                print(f"[Scheduler] Executed scheduled post to {platform}")
                self._execute_post(platform, social_data)

            threading.Thread(target=mock_delay, daemon=True).start()
            return {"status": "success", "message": f"Post scheduled for {post_time}"}

    def _execute_post(self, platform: str, social_data: dict):
        print("\n" + "="*50)
        print(f"🚀 [SOCIAL MEDIA API] EXECUTING POST TO {platform.upper()}")
        print("="*50)
        
        if platform in ["both", "instagram"] and "instagram" in social_data:
            ig = social_data["instagram"]
            print(f"[Instagram]")
            print(f"Caption: {ig.get('caption', '')[:100]}...")
            print(f"Image attached: {'Yes (base64 length ' + str(len(ig.get('image_b64', ''))) + ')' if ig.get('image_b64') else 'No'}")
            print("-" * 50)
            
        if platform in ["both", "linkedin"] and "linkedin" in social_data:
            li = social_data["linkedin"]
            print(f"[LinkedIn]")
            print(f"Post Text: {li.get('post_text', '')[:100]}...")
            print(f"Image attached: {'Yes (base64 length ' + str(len(li.get('image_b64', ''))) + ')' if li.get('image_b64') else 'No'}")
            print("-" * 50)

def get_scheduled_posts():
    return scheduled_posts
