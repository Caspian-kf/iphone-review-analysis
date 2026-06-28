async function loadReviews() {
  const reviewsElement = document.getElementById("reviews");

  if (!reviewsElement) {
    return;
  }

  try {
    const response = await fetch("../data/reviews.json");
    const reviews = await response.json();
    reviewsElement.textContent = JSON.stringify(reviews, null, 2);
  } catch (error) {
    reviewsElement.textContent = "Unable to load reviews.json";
  }
}

loadReviews();
