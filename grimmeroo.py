#
# Author: Riccardo Orizio
# Date: Tue 21 Jul 2020
# Description: Getting blueprints information from Grim Dawn wiki and returning
# the amount of crafting materials needed to craft them
#

import argparse
from bs4 import BeautifulSoup
import pickle
import re
from typing import Dict, List
import urllib.request

# Constants
GRIM_DAWN_BASE = "https://grimdawn.fandom.com"
GRIM_DAWN_WIKI = "https://grimdawn.fandom.com/wiki/Blueprints"
LOCAL_DB = "./blue.prints"
REGEX_INGREDIENT = r"([^(]*)\((\d+)\)"

# Classes
class Blueprint:
    def __init__( self ):
        self.name = ""
        self.type = ""
        self.materials = {}

    def materials_list( self ) -> List[ str ]:
        """ Returning a list of all the components with items repeated by their quantity

        :return: The list of materials
        :rtype: List[ str ]
        """

        result = [ [ mat ] * qty for mat, qty in self.materials.items() ]
        return [ sublist for l in result for sublist in l ]

    def __str__( self ):
        return "{}({}) [{}]".format( self.name,
                                     self.type,
                                     ", ".join( "{}x{}".format( v, k ) for k, v in self.materials.items() ) )

    def __repr__( self ):
        return str( self )


class Blueprints:
    def __init__( self ):
        self.blueprints = {}
        try:
            self.blueprints = pickle.load( open( LOCAL_DB, "rb" ) )
        except FileNotFoundError:
            print( "Local DB not found, downloading from Grim Dawn wiki: {}".format( GRIM_DAWN_WIKI ) )
            self.read_all_blueprints( GRIM_DAWN_WIKI )
            with open( LOCAL_DB, "wb" ) as output_file:
                pickle.dump( self.blueprints, output_file )

    def create_blueprint( self,
                          link: str,
                          item_type: str = None ) -> Blueprint:
        """ Creating a blueprint item from the given link
    
        :param link: Link to the current blueprint
        :type: str
        :param item_type: Type of the blueprint
        :type: str, optional, default = None
        :return: The created Blueprint instance
        :rtype: Blueprint
        """
    
        current_content = BeautifulSoup( urllib.request.urlopen( link ).read(), # open( link, "r" ),  
                                         "html.parser" )
    
        result = Blueprint()
        blueprint_info = current_content.find_all( "h1" )[ 0 ].text
        result.name = blueprint_info.replace( "Blueprint: ", "" )
        result.name = result.name.replace( "Relic - ", "" )
        if item_type is not None:
            result.type = item_type 
    
        ingredients = current_content.find_all( "table" )[ 0 ].find_all( "td" )
        ingredients = [ i for i in ingredients if i.text ]
        for ingredient in ingredients:
            if "crafts" in ingredient.text.lower():
                break
            print( "\t- '{}'".format( ingredient.text ) )
            current_ingredient = re.findall( REGEX_INGREDIENT, ingredient.text )
            if len( current_ingredient ) > 0:
                result.materials[ current_ingredient[ 0 ][ 0 ][ :-1 ] ] = int( current_ingredient[ 0 ][ 1 ] )
    
        return result
    
    def read_all_blueprints( self,
                             link: str ) -> int:
        """ Reading info of all blueprints from the given link (Wiki)
    
        :param link: Link to the Grim Dawn blueprint list
        :type: str
        :return: The number of created Blueprint list
        :rtype: int
        """
    
        page_content = BeautifulSoup( urllib.request.urlopen( GRIM_DAWN_WIKI ).read(),
                                      "html.parser" )
        
        blueprints = [ link for link in page_content.find_all( "a" )
                            if "blueprint:" in link.text.lower() ]

        print( "{} blueprints found".format( len( blueprints ) ) )
        for blueprint in blueprints:
            print( " - Analysing '{}'".format( blueprint ) )
            self.add_blueprint( self.create_blueprint( GRIM_DAWN_BASE + blueprint.get( "href" ) ) )

        #   titles = [ t for t in page_content.find_all( "h2" )
        #              if "blueprint" in t.text.lower() ]
        #   tables = [ t for t in page_content.find_all( "table" )
        #              if len( t.find_all( "th" ) ) > 1 and "blueprint" in t.find_all( "th" )[ 2 ].text.lower() ][ :-1 ]

        #   for i, j in zip( titles, tables ):
        #       item_type = i.find( "span" ).get( "id" ).replace( "Blueprints:", "" ).replace( "_", " " ).strip()
        #       for blueprint in [ link for link in j.find_all( "a" ) if link.get( "title" ) is not None ]:
        #           print( " - Analysing ({}) '{}'".format( item_type, blueprint ) )
        #           self.add_blueprint( self.create_blueprint( GRIM_DAWN_BASE + blueprint.get( "href" ),
        #                                                      item_type ) )
        
    
        return len( self.blueprints )

    def add_blueprint( self,
                       blueprint: Blueprint ) -> None:
        """ Adding the blueprint

        :param blueprint: Blueprint instance to add
        :type: Blueprint
        :return: None
        :rtype: None
        """

        if blueprint.name in self.blueprints:
            print( "WARNING! '{}' seems to already be part of the DB!" )
        self.blueprints[ blueprint.name ] = blueprint
    
    def find_keyword( self,
                      keyword: str ) -> Dict[ str, Dict[ str, int ] ]:
        """ Finding all materials needed to craft a particular item given by a keyword
    
        :param keyword: Keyword to use to locate the items
        :type: str
        :param blueprints: Blueprints database
        :type: List[ Blueprint ]
        :return: Mapping between items found ant their needed materials with quantities
        :rtype: Dict[ str, Dict[ str, int ] ]
        """
    
        blueprint_matches = [ k for k in self.blueprints.keys() if keyword.lower() in k.lower() ]
        return { k: pack_list( self.find_materials( k ) ) for k in blueprint_matches }
    
    
    def find_materials( self,
                        item_name: str ) -> List[ str ]:
        """ Finding the materials needed for a given blueprint
    
        :param item_name: Blueprint to analyse
        :type: str
        :return: List of raw materials needed to craft the given blueprint
        :rtype: List[ str ]
        """
    
        result = self.blueprints[ item_name ].materials_list()
        to_remove = []
        for idx, material in enumerate( result ):
            if material in self.blueprints:
                result.extend( self.blueprints[ material ].materials_list() )
                to_remove.append( idx )

        return [ result[ i ] for i in range( len( result ) ) if i not in to_remove ]

    def size( self ) -> int:
        """ Return the number of blueprints stored

        :return: Number of blueprints
        :rtype: int
        """

        return len( self.blueprints )

# Functions
def pack_list( a_list: List[ str ] ) -> Dict[ str, int ]:
    """ Packing a list of repeated items into a dictionary

    :param a_list: A list to pack
    :type: List[ str ]
    :return: Mapping between value and quantity of the items in the list
    :rtype: Dict[ str, int ]
    """

    return { k: a_list.count( k ) for k in set( a_list ) }

# Main
def main():
    #   sbra = create_blueprint( "./Blueprint_Maivens_Lens.html" )
    #   print( str( sbra ) )
    #   exit( 3 )
    
    arg_parser = argparse.ArgumentParser( description="Script to find the materials needed to craft Grim Dawn blueprints" )
    arg_parser.add_argument( "--keyword",
                             dest="keyword",
                             default=None,
                             type=str,
                             help="Keywork for the blueprint of interest" )

    input_args = vars( arg_parser.parse_args() )


    if input_args[ "keyword" ] is not None:
        blueprints = Blueprints()
        print( "Database of {} Blueprints loaded".format( blueprints.size() ) )
    
        for blueprint, materials in blueprints.find_keyword( input_args[ "keyword" ] ).items():
            print( "'{}':\n{}".format( blueprint, "\n".join( " - {} {}".format( v, k ) for k, v in materials.items() ) ) )
    else:
        print( "Please insert keyword to look for in the database" )


if __name__ == "__main__":
    main()

