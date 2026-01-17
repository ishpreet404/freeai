"""
Test script for movie search functionality
Tests the TMDB API and movie search without needing Discord bot running
"""

from tmdbv3api import TMDb, Movie
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize TMDB
tmdb = TMDb()
tmdb.api_key = 'ae4bd1b6fce2a5648671bfc171d15ba4'
tmdb.language = 'en'
movie_api = Movie()

def test_movie_search(query):
    """Test movie search functionality"""
    print(f"\n{'='*60}")
    print(f"Searching for: {query}")
    print(f"{'='*60}")
    
    try:
        # Search TMDB
        results = movie_api.search(query)
        
        if not results:
            print(f"❌ No movies found for: {query}")
            return
        
        print(f"\n✅ Found {len(results)} results\n")
        
        # Get details of first result
        results_list = list(results)
        if not results_list:
            print(f"❌ No movies found for: {query}")
            return
        
        movie = results_list[0]
        movie_details = movie_api.details(movie.id)
        
        # Get external IDs for IMDb
        external_ids = movie_api.external_ids(movie.id)
        imdb_id = external_ids.get('imdb_id', None)
        
        # Safely get release year
        release_year = movie_details.release_date[:4] if hasattr(movie_details, 'release_date') and movie_details.release_date else 'N/A'
        
        # Safely get overview
        overview = movie_details.overview if hasattr(movie_details, 'overview') else "No overview available."
        
        # Display results
        print(f"Title: {movie_details.title} ({release_year})")
        print(f"TMDB ID: {movie.id}")
        print(f"IMDb ID: {imdb_id if imdb_id else 'N/A'}")
        print(f"Rating: {movie_details.vote_average:.1f}/10")
        
        if hasattr(movie_details, 'runtime') and movie_details.runtime:
            print(f"Runtime: {movie_details.runtime} min")
        
        if hasattr(movie_details, 'genres') and movie_details.genres:
            genres_list = list(movie_details.genres)
            genres = ", ".join([g.name for g in genres_list[:3]])
            print(f"Genres: {genres}")
        
        print(f"\nOverview: {overview[:200]}...")
        
        if movie_details.poster_path:
            print(f"Poster: https://image.tmdb.org/t/p/w500{movie_details.poster_path}")
        
        print(f"TMDB URL: https://www.themoviedb.org/movie/{movie.id}")
        
        # Test streaming URLs for all providers
        print(f"\nStreaming URLs:")
        
        # All streaming providers
        providers = {
            'vidsrc': 'VidSrc (Recommended)',
            'vixsrc': 'VixSrc',
            'godrive': 'GoDrive Player',
            'embedsu': 'Embed.su',
            '2embed': '2Embed',
            'vidfast': 'VidFast'
        }
        
        for provider_key, provider_name in providers.items():
            if provider_key == 'vixsrc':
                url = f"https://vixsrc.to/movie/{movie.id}"
            elif provider_key == 'vidsrc':
                url = f"https://vidsrc.to/embed/movie/{imdb_id if imdb_id else movie.id}"
            elif provider_key == 'godrive':
                url = f"https://godriveplayer.com/player.php?imdb={imdb_id}" if imdb_id else f"https://godriveplayer.com/player.php?tmdb={movie.id}"
            elif provider_key == 'embedsu':
                url = f"https://embed.su/embed/movie/{movie.id}"
            elif provider_key == '2embed':
                url = f"https://www.2embed.cc/embed/{imdb_id if imdb_id else movie.id}"
            elif provider_key == 'vidfast':
                url = f"https://vidfast.pro/movie/{movie.id}?autoPlay=true"
            else:
                url = "N/A"
            
            print(f"  {provider_name}: {url}")
        
        print(f"\n{'='*60}")
        print(f"✅ Test passed successfully!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ Error: {str(e)}")
        print(f"{'='*60}\n")
        logger.error(f"Movie search error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("\n🎬 TMDB Movie Search Test\n")
    
    # Test cases - only valid movies
    test_cases = [
        "Inception",
        "The Matrix",
        "Interstellar"
    ]
    
    for query in test_cases:
        test_movie_search(query)
        if query != test_cases[-1]:  # Don't wait after last test
            input("\nPress Enter to continue to next test...")
    
    print("\n✅ All tests completed!")
