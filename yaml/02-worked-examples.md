# YAML: Worked Examples

> Complete YAML documents (family tree, hobby tracker, travel planner) that combine maps, lists, and nesting.

## Key Concepts

### A Family Tree Example

Representing relationships and hierarchical data:

```yaml
family:
  name: The Smiths
  members:
    - name: James Smith
      role: Father
      age: 42
      hobbies:
        - Woodworking
        - Gardening
        - Chess

    - name: Maria Smith
      role: Mother
      age: 40
      hobbies:
        - Painting
        - Running
        - Cooking

    - name: Emma Smith
      role: Daughter
      age: 15
      hobbies:
        - Volleyball
        - Piano
        - Reading
      school: Lincoln High School

    - name: Alex Smith
      role: Son
      age: 10
      hobbies:
        - Soccer
        - Video games
        - Science experiments
      school: Washington Elementary

  pets:
    - name: Max
      type: Dog
      breed: Golden Retriever
      age: 5
    - name: Whiskers
      type: Cat
      breed: Maine Coon
      age: 3
```

### A Hobby Tracker Example

```yaml
hobby_tracker:
  user: taylor_garcia
  categories:
    books:
      currently_reading:
        - title: The Midnight Library
          author: Matt Haig
          pages: 304
          progress: 75%
      completed_this_year:
        - title: Project Hail Mary
          author: Andy Weir
          rating: 5
        - title: Educated
          author: Tara Westover
          rating: 4.5
      want_to_read:
        - Cloud Atlas
        - The Three-Body Problem
        - Klara and the Sun

    fitness:
      weekly_goals:
        running:
          distance_km: 20
          current_progress: 12.5
        strength_training:
          sessions: 3
          completed: 2
      personal_records:
        5k_time: "22:45"
        deadlift_kg: 120

    cooking:
      favorite_recipes:
        - name: Vegetable Curry
          cuisine: Indian
          last_made: "2025-04-12"
        - name: Sourdough Bread
          cuisine: Artisan
          last_made: "2025-04-30"
      recipes_to_try:
        - Ramen from scratch
        - Thai Green Curry
        - Homemade Pasta
```

### A Travel Planner Example

```yaml
travel_plans:
  destination: Japan
  duration_days: 14
  travelers:
    - name: Emma Wilson
      passport: AB123456
      dietary_restrictions: Vegetarian
    - name: Marcus Wilson
      passport: CD789012
      dietary_restrictions: None

  itinerary:
    - day: 1
      date: 2025-06-10
      location: Tokyo
      accommodations:
        name: Shibuya Excel Hotel
        confirmation: TMY6789
      activities:
        - time: "14:00"
          activity: Check-in at hotel
        - time: "16:00"
          activity: Explore Shibuya Crossing
        - time: "19:00"
          activity: Welcome dinner at Ichiran Ramen
          reservation: true
          confirmation: RMN4532

    - day: 2
      date: 2025-06-11
      location: Tokyo
      accommodations:
        name: Shibuya Excel Hotel
        confirmation: TMY6789
      activities:
        - time: "09:00"
          activity: Tsukiji Outer Market
        - time: "13:00"
          activity: Meiji Shrine
        - time: "16:00"
          activity: Harajuku shopping
        - time: "20:00"
          activity: Dinner at Gonpachi
          reservation: true
          confirmation: GPC7812

  budget:
    currency: USD
    categories:
      flights: 1800
      accommodations: 2200
      food: 1000
      activities: 800
      shopping: 500
      contingency: 700
    total: 7000

  packing_list:
    documents:
      - Passport
      - Flight tickets
      - Hotel reservations
      - Travel insurance
    clothing:
      - T-shirts: 7
      - Pants: 3
      - Dresses: 2
      - Jackets: 1
      - Walking shoes: 1
      - Formal shoes: 1
    electronics:
      - Camera
      - Smartphone
      - Universal adapter
      - Power bank
```
